import os
import json
import requests

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
SOURCE_REPO = os.getenv("SOURCE_REPO")  # e.g. "owner/repo"
TARGET_REPO = os.getenv("TARGET_REPO")
DEFAULT_CLOSE_COMMENT = os.getenv("DEFAULT_CLOSE_COMMENT") or ""
GITHUB_EVENT_PATH = os.getenv("GITHUB_EVENT_PATH")
GITHUB_API = "https://api.github.com"

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

def gh_request(method, url, **kwargs):
    resp = requests.request(method, url, headers=HEADERS, **kwargs)
    if resp.status_code >= 400:
        print(f"ERROR {method} {url} -> {resp.status_code} {resp.text}")
        resp.raise_for_status()
    return resp

if not GITHUB_EVENT_PATH:
    print("Missing GITHUB_EVENT_PATH.")
    exit(1)

with open(GITHUB_EVENT_PATH, "r", encoding="utf-8") as f:
    event = json.load(f)

event_repo = os.environ.get("GITHUB_REPOSITORY")  # event repo owner/repo
event_action = event.get("action")
issue = event.get("issue", {})
issue_num = issue.get("number")
issue_state = issue.get("state")
issue_title = issue.get("title") or "[No title]"
issue_body = issue.get("body") or ""
issue_labels = [label["name"].lower() for label in issue.get("labels", [])]

mirror_tag = f"[Mirrored from original issue](https://github.com/{SOURCE_REPO}/issues/{issue_num})"
reverse_tag = f"[Mirrored from original issue](https://github.com/{TARGET_REPO}/issues/{issue_num})"

def find_mirror(repo, tag):
    url = f"{GITHUB_API}/repos/{repo}/issues?state=all&per_page=100"
    while url:
        resp = gh_request("GET", url)
        issues = resp.json()
        for i in issues:
            if tag in (i.get("body") or ""):
                return i["number"]
        # pagination
        url = resp.links.get("next", {}).get("url")
    return None

def create_issue(repo, title, body):
    url = f"{GITHUB_API}/repos/{repo}/issues"
    resp = gh_request("POST", url, json={"title": title, "body": body})
    return resp.json()["number"]

def update_issue(repo, issue_number, title=None, body=None, state=None):
    url = f"{GITHUB_API}/repos/{repo}/issues/{issue_number}"
    data = {}
    if title is not None:
        data["title"] = title
    if body is not None:
        data["body"] = body
    if state is not None:
        data["state"] = state
    gh_request("PATCH", url, json=data)

def add_comment(repo, issue_number, comment_body):
    url = f"{GITHUB_API}/repos/{repo}/issues/{issue_number}/comments"
    gh_request("POST", url, json={"body": comment_body})

def get_comments(repo, issue_number):
    url = f"{GITHUB_API}/repos/{repo}/issues/{issue_number}/comments?per_page=100"
    resp = gh_request("GET", url)
    return resp.json()

def close_target_due_to_source_deletion(target_repo, target_issue_num):
    close_comment = "Source issue deleted — closing mirrored issue."
    add_comment(target_repo, target_issue_num, close_comment)
    update_issue(target_repo, target_issue_num, state="closed")

def mirror_comments(src_repo, dst_repo, src_issue_num, dst_issue_num):
    src_comments = get_comments(src_repo, src_issue_num)
    dst_comments = get_comments(dst_repo, dst_issue_num)
    dst_bodies = [c["body"] for c in dst_comments]
    for c in src_comments:
        tag = f"[Mirrored from comment](https://github.com/{src_repo}/issues/{src_issue_num}#issuecomment-{c['id']})"
        body = f"_@{c['user']['login']} wrote:_\n\n{c['body']}\n\n{tag}"
        if tag not in dst_bodies:
            add_comment(dst_repo, dst_issue_num, body)

def close_reasons_from_labels(labels):
    # Return close reason comment or None
    if "duplicate" in labels:
        return "Closed as duplicate."
    if "completed" in labels:
        return "Closed as completed."
    if "not planned" in labels:
        return "Closed as not planned."
    return None

def mirror_issue_to_target():
    mirror_num = find_mirror(TARGET_REPO, mirror_tag)
    body = (issue_body or "") + "\n\n" + mirror_tag

    if event_action == "deleted":
        if mirror_num:
            close_target_due_to_source_deletion(TARGET_REPO, mirror_num)
        return

    if mirror_num:
        # update mirrored issue
        update_issue(TARGET_REPO, mirror_num, title=issue_title, body=body)
        # reopen if source is open and mirrored closed
        if issue_state == "open":
            update_issue(TARGET_REPO, mirror_num, state="open")
        # close if source is closed
        if issue_state == "closed":
            # add close reason comment if any
            reason = close_reasons_from_labels(issue_labels) or DEFAULT_CLOSE_COMMENT
            if reason:
                add_comment(TARGET_REPO, mirror_num, reason)
            update_issue(TARGET_REPO, mirror_num, state="closed")
        mirror_comments(SOURCE_REPO, TARGET_REPO, issue_num, mirror_num)
    else:
        # create mirrored issue if source open
        if issue_state == "open":
            new_num = create_issue(TARGET_REPO, issue_title, body)
            mirror_comments(SOURCE_REPO, TARGET_REPO, issue_num, new_num)

def mirror_close_to_source():
    mirror_num = find_mirror(SOURCE_REPO, reverse_tag)
    if not mirror_num:
        return

    # When target issue closes, close source issue but DO NOT post default-close-comment
    if issue_state == "closed":
        # add close reason comment only if close reason label found on target issue
        reason = None
        # Get target issue labels:
        target_issue_url = f"{GITHUB_API}/repos/{TARGET_REPO}/issues/{issue_num}"
        resp = gh_request("GET", target_issue_url)
        target_labels = [label["name"].lower() for label in resp.json().get("labels", [])]

        if "duplicate" in target_labels:
            reason = "Closed as duplicate."
        elif "completed" in target_labels:
            reason = "Closed as completed."
        elif "not planned" in target_labels:
            reason = "Closed as not planned."

        if reason:
            add_comment(SOURCE_REPO, mirror_num, reason)
        update_issue(SOURCE_REPO, mirror_num, state="closed")

def main():
    if not issue_num:
        print("No issue number found in event.")
        return

    if event_repo == SOURCE_REPO:
        mirror_issue_to_target()

    elif event_repo == TARGET_REPO:
        # Bidirectional close syncing (only close)
        if event_action in ["closed", "reopened"]:
            mirror_close_to_source()

if __name__ == "__main__":
    main()
