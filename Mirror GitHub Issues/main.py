import os
import json
import requests

GITHUB_TOKEN = os.getenv("INPUT_GITHUB_TOKEN")
SOURCE_REPO = os.getenv("INPUT_SOURCE_REPO")
TARGET_REPO = os.getenv("INPUT_TARGET_REPO")
GITHUB_EVENT_PATH = os.environ.get("GITHUB_EVENT_PATH")
GITHUB_API = "https://api.github.com"

print(f"GITHUB_TOKEN: {'set' if GITHUB_TOKEN else 'missing'}")
print(f"SOURCE_REPO: {SOURCE_REPO}")
print(f"TARGET_REPO: {TARGET_REPO}")

if not GITHUB_EVENT_PATH:
    print("Missing GITHUB_EVENT_PATH.")
    exit(1)

with open(GITHUB_EVENT_PATH, 'r') as f:
    event = json.load(f)

issue = event.get("issue", {})
issue_number = issue.get("number")
issue_title = issue.get("title") or "[No title]"
issue_body = issue.get("body") or ""
issue_state = issue.get("state")

mirror_tag = f"[Mirrored from {SOURCE_REPO}#{issue_number}]"

headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

def find_mirrored_issue():
    url = f"{GITHUB_API}/repos/{TARGET_REPO}/issues"
    params = {"state": "all", "per_page": 100}
    print(f"Checking for existing mirrored issues at: {url}")
    resp = requests.get(url, headers=headers, params=params)
    resp.raise_for_status()
    for i in resp.json():
        if mirror_tag in (i.get("body") or ""):
            print(f"Found mirrored issue: #{i['number']}")
            return i["number"]
    print("No mirrored issue found.")
    return None

def create_issue():
    url = f"{GITHUB_API}/repos/{TARGET_REPO}/issues"
    body = f"{issue_body}\n\n---\n{mirror_tag}" if issue_body else mirror_tag
    data = {
        "title": issue_title,
        "body": body
    }
    print("Creating issue with data:")
    print(json.dumps(data, indent=2))
    resp = requests.post(url, headers=headers, json=data)
    try:
        resp.raise_for_status()
    except requests.exceptions.HTTPError:
        print("Failed to create issue.")
        print("Status Code:", resp.status_code)
        print("Response:", resp.text)
        raise
    number = resp.json()["number"]
    print(f"Issue created: #{number}")
    return number

def update_issue(mirror_issue_number):
    url = f"{GITHUB_API}/repos/{TARGET_REPO}/issues/{mirror_issue_number}"
    body = f"{issue_body}\n\n---\n{mirror_tag}" if issue_body else mirror_tag
    data = {
        "title": issue_title,
        "body": body
    }
    print(f"Updating issue #{mirror_issue_number}")
    resp = requests.patch(url, headers=headers, json=data)
    resp.raise_for_status()
    print(f"Issue #{mirror_issue_number} updated")

def close_issue(mirror_issue_number):
    url = f"{GITHUB_API}/repos/{TARGET_REPO}/issues/{mirror_issue_number}"
    data = {"state": "closed"}
    print(f"Closing issue #{mirror_issue_number}")
    resp = requests.patch(url, headers=headers, json=data)
    resp.raise_for_status()
    print(f"Issue #{mirror_issue_number} closed")

def main():
    mirrored = find_mirrored_issue()
    if mirrored is None:
        if issue_state == "open":
            create_issue()
        else:
            print("Issue is closed and not mirrored yet.")
    else:
        if issue_state == "closed":
            close_issue(mirrored)
        else:
            update_issue(mirrored)

if __name__ == "__main__":
    main()
