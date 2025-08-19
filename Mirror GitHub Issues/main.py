import os
import json
import requests

# Required environment variables
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
SOURCE_REPO = os.getenv("SOURCE_REPO")
TARGET_REPO = os.getenv("TARGET_REPO")
DEFAULT_CLOSE_COMMENT = os.getenv("DEFAULT_CLOSE_COMMENT") or ""
GITHUB_EVENT_PATH = os.getenv("GITHUB_EVENT_PATH")
GITHUB_API = "https://api.github.com"

# Standard headers
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}
REACT_HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.squirrel-girl-preview+json"
}

if not GITHUB_EVENT_PATH:
    print("Missing GITHUB_EVENT_PATH.")
    exit(1)

with open(GITHUB_EVENT_PATH, 'r') as f:
    event = json.load(f)

event_repo = os.environ.get("GITHUB_REPOSITORY")

issue = event.get("issue", {})
issue_num = issue.get("number")
issue_title = issue.get("title") or "[No title]"
issue_body = issue.get("body") or ""
issue_state = issue.get("state")
comment = event.get("comment")
reaction = event.get("reaction")

mirror_tag = f"[Mirrored from original issue](https://github.com/{SOURCE_REPO}/issues/{issue_num})"

def gh_request(method, url, headers, **kwargs):
    resp = requests.request(method, url, headers=headers, **kwargs)
    if resp.status_code >= 400:
        print(f"{method} {url} failed: {resp.status_code} - {resp.text}")
        resp.raise_for_status()
    return resp

def find_mirror(repo, tag):
    url = f"{GITHUB_API}/repos/{repo}/issues"
    resp = gh_request("GET", url, HEADERS, params={"state": "all", "per_page": 100})
    for issue in resp.json():
        if tag in (issue.get("body") or ""):
            return issue["number"]
    return None

def mirror_issue(repo):
    mirror_id = find_mirror(repo, mirror_tag)
    body = f"{issue_body}\n\n{mirror_tag}" if issue_body else mirror_tag

    if not mirror_id and issue_state == "open":
        resp = gh_request("POST", f"{GITHUB_API}/repos/{repo}/issues", HEADERS, json={
            "title": issue_title,
            "body": body
        })
        mirror_id = resp.json()["number"]

    elif mirror_id:
        gh_request("PATCH", f"{GITHUB_API}/repos/{repo}/issues/{mirror_id}", HEADERS, json={
            "title": issue_title,
            "body": body
        })
        if issue_state == "closed":
            if DEFAULT_CLOSE_COMMENT:
                gh_request("POST", f"{GITHUB_API}/repos/{repo}/issues/{mirror_id}/comments", HEADERS, json={
                    "body": DEFAULT_CLOSE_COMMENT
                })
            gh_request("PATCH", f"{GITHUB_API}/repos/{repo}/issues/{mirror_id}", HEADERS, json={
                "state": "closed"
            })

    return mirror_id

def mirror_comments(src_repo, dst_repo, src_issue, dst_issue):
    src_comments = gh_request("GET", f"{GITHUB_API}/repos/{src_repo}/issues/{src_issue}/comments", HEADERS).json()
    dst_comments = gh_request("GET", f"{GITHUB_API}/repos/{dst_repo}/issues/{dst_issue}/comments", HEADERS).json()
    dst_bodies = [c["body"] for c in dst_comments]

    for comment in src_comments:
        tag = f"[Mirrored from comment](https://github.com/{src_repo}/issues/{src_issue}#issuecomment-{comment['id']})"
        body = f"_@{comment['user']['login']} wrote:_\n\n{comment['body']}\n\n{tag}"
        if tag not in dst_bodies:
            gh_request("POST", f"{GITHUB_API}/repos/{dst_repo}/issues/{dst_issue}/comments", HEADERS, json={
                "body": body
            })

def mirror_reactions(src_repo, dst_repo, src_type, src_id, dst_type, dst_id):
    url_src = f"{GITHUB_API}/repos/{src_repo}/{src_type}/{src_id}/reactions"
    reactions = gh_request("GET", url_src, REACT_HEADERS).json()

    for reaction in reactions:
        url_dst = f"{GITHUB_API}/repos/{dst_repo}/{dst_type}/{dst_id}/reactions"
        try:
            gh_request("POST", url_dst, REACT_HEADERS, json={
                "content": reaction["content"]
            })
        except requests.exceptions.HTTPError as e:
            if "409" in str(e):
                print("Duplicate reaction, skipping.")
            else:
                raise

def main():
    if not issue_num:
        print("No issue found in event.")
        return

    if event_repo == SOURCE_REPO:
        mirror_id = mirror_issue(TARGET_REPO)
        if mirror_id:
            mirror_comments(SOURCE_REPO, TARGET_REPO, issue_num, mirror_id)
            mirror_reactions(SOURCE_REPO, TARGET_REPO, "issues", issue_num, "issues", mirror_id)

    elif event_repo == TARGET_REPO:
        reverse_tag = f"[Mirrored from original issue](https://github.com/{TARGET_REPO}/issues/{issue_num})"
        source_id = find_mirror(SOURCE_REPO, reverse_tag)
        if source_id and issue_state == "closed":
            if DEFAULT_CLOSE_COMMENT:
                gh_request("POST", f"{GITHUB_API}/repos/{SOURCE_REPO}/issues/{source_id}/comments", HEADERS, json={
                    "body": DEFAULT_CLOSE_COMMENT
                })
            gh_request("PATCH", f"{GITHUB_API}/repos/{SOURCE_REPO}/issues/{source_id}", HEADERS, json={
                "state": "closed"
            })

if __name__ == "__main__":
    main()
