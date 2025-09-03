import os
import sys
import requests
import fnmatch

# ANSI styles
RESET = '\033[0m'
BOLD = '\033[1m'

BRIGHT_RED = '\033[91m'
BRIGHT_GREEN = '\033[92m'
BRIGHT_CYAN = '\033[96m'

def print_error(msg):
    print(f"{BRIGHT_RED}{BOLD}ERROR: {msg}{RESET}", file=sys.stderr)
    sys.exit(1)

def print_success(msg):
    print(f"{BRIGHT_GREEN}{BOLD}{msg}{RESET}")

def print_info(msg):
    print(f"{BRIGHT_CYAN}{msg}{RESET}")

GITHUB_API = "https://api.github.com"

def get_lines(env_var):
    val = os.getenv(env_var, "")
    return [line.strip() for line in val.strip().splitlines() if line.strip() and not line.strip().startswith("#")]

def matches_pattern(name, pattern):
    if "*" in pattern or "?" in pattern:
        return fnmatch.fnmatch(name, pattern)
    return name == pattern

def get_latest_successful_run(repo, token, workflow, branch):
    url = f"{GITHUB_API}/repos/{repo}/actions/workflows/{workflow}/runs"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"status": "success", "branch": branch, "per_page": 1}

    r = requests.get(url, headers=headers, params=params)
    r.raise_for_status()

    runs = r.json().get("workflow_runs", [])
    if not runs:
        print_info(f"No successful runs found for {workflow} on branch {branch}")
        sys.exit(0)

    return runs[0]["id"]

def list_artifacts(repo, token, run_id):
    url = f"{GITHUB_API}/repos/{repo}/actions/runs/{run_id}/artifacts"
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json().get("artifacts", [])

def download_artifact(repo, token, artifact, output_dir):
    url = artifact["archive_download_url"]
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }

    r = requests.get(url, headers=headers)
    r.raise_for_status()

    name = artifact["name"]
    path = os.path.join(output_dir, f"{name}.zip")
    os.makedirs(output_dir, exist_ok=True)

    with open(path, "wb") as f:
        f.write(r.content)

    print_success(f"Downloaded: {name} -> {path}")

def main():
    repo = os.getenv("GITHUB_REPOSITORY")
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print_error("GITHUB_TOKEN not provided.")

    workflows = get_lines("workflows")
    artifact_patterns = get_lines("artifacts")
    branch = os.getenv("branch", "main")
    output_dir = os.getenv("output", "artifacts")

    any_downloaded = False

    for workflow in workflows:
        print_info(f"Checking workflow: {workflow}")
        run_id = get_latest_successful_run(repo, token, workflow, branch)
        if not run_id:
            continue

        artifacts = list_artifacts(repo, token, run_id)
        if not artifacts:
            print_info(f"No artifacts found for workflow {workflow} run {run_id}")
            continue

        matched = False
        for artifact in artifacts:
            name = artifact["name"]
            if any(matches_pattern(name, pat) for pat in artifact_patterns):
                print_info(f"Downloading: {name}")
                download_artifact(repo, token, artifact, output_dir)
                any_downloaded = True
                matched = True

        if not matched:
            print_info("No artifacts found matching the given patterns.")

    if not any_downloaded:
        sys.exit(0)

if __name__ == "__main__":
    main()
