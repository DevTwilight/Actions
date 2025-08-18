import os
import json
import requests

# Load environment variables passed from the action
GITHUB_TOKEN = os.getenv("INPUT_GITHUB_TOKEN")
SOURCE_REPO = os.getenv("INPUT_SOURCE_REPO")
TARGET_REPO = os.getenv("INPUT_TARGET_REPO")
GITHUB_EVENT_PATH = os.getenv("GITHUB_EVENT_PATH")
GITHUB_API = "https://api.github.com"

# Debug output
print(f"GITHUB_TOKEN: {'set' if GITHUB_TOKEN else 'missing'}")
print(f"SOURCE_REPO: {SOURCE_REPO}")
print(f"TARGET_REPO: {TARGET_REPO}")

# Check for required env
if not GITHUB_EVENT_PATH:
    print("Missing GITHUB_EVENT_PATH.")
    exit(1)

# Load GitHub event payload
with open(GITHUB_EVENT_PATH, 'r') as f:
    event = json.load(f)

# Get issue details
issue = event.get("issue", {})
issue_number = issue.get("number")
issue_title = issue.get("title")
issue_body = issue.get("body", "")
issue_action = event.get("action")  # <- CORRECT field to use

# Mirror tag to identify related issues
mirror_tag = f"[Mirrored from {SOURCE_REPO}#{issue_number}]"

# HTTP headers
headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

def find_mirrored_issue():
    url = f"{GITHUB_API}/repos/{TARGET_REPO}/issues"
    params = {"state": "all", "per_page": 100}
    resp = requests.get(url, headers=headers, params=params)
    resp.raise_for_status()
    for i in resp.json():
        if mirror_tag in (i.get("body") or ""):
            return i["number"]
    return None

def create_issue():
    url = f"{GITHUB_API}/repos/{TARGET_REPO}/issues"
    data = {
        "title": issue_title,
        "body": f"{issue_body}\n\n---\n{mirror_tag}"
    }
    resp = requests.post(url, headers=headers, json=data)
    resp.raise_for_status()
    issue_number = resp.json()["number"]
    print(f"Issue #{issue_number} created in {TARGET_REPO}")
    return issue_number

def update_issue(mirror_issue_number):
    url = f"{GITHUB_API}/repos/{TARGET_REPO}/issues/{mirror_issue_number}"
    data = {
        "title": issue_title,
        "body": f"{issue_body}\n\n---\n{mirror_tag}"
    }
    resp = requests.patch(url, headers=headers, json=data)
    resp.raise_for_status()
    print(f"Issue #{mirror_issue_number} updated in {TARGET_REPO}")

def close_issue(mirror_issue_number):
    url = f"{GITHUB_API}/repos/{TARGET_REPO}/issues/{mirror_issue_number}"
    data = {"state": "closed"}
    resp = requests.patch(url, headers=headers, json=data)
    resp.raise_for_status()
    print(f"Issue #{mirror_issue_number} closed in {TARGET_REPO}")

def main():
    mirrored = find_mirrored_issue()

    if mirrored is None:
        new_number = create_issue()
        if issue_action == "closed":
            close_issue(new_number)
    else:
        if issue_action == "closed":
            close_issue(mirrored)
        else:
            update_issue(mirrored)

if __name__ == "__main__":
    main()
