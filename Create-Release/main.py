import os
import re
import subprocess
import sys

RESET = '\033[0m'
BRIGHT_RED = '\033[91m'
BRIGHT_GREEN = '\033[38;5;10m'
BRIGHT_YELLOW = '\033[96m'

def log_info(msg):
    print(f"{BRIGHT_YELLOW}[INFO]{RESET} {msg}")

def log_success(msg):
    print(f"{BRIGHT_GREEN}[SUCCESS]{RESET} {msg}")

def log_error(msg):
    print(f"{BRIGHT_RED}[ERROR]{RESET} {msg}", file=sys.stderr)

def is_prerelease(tag: str) -> bool:
    match = re.search(r'-(.+)$', tag)
    if not match:
        return False
    suffix = match.group(1).lower()
    return suffix not in ['stable', 'release']

def run(cmd):
    log_info(f"Running command: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        log_error(f"Command failed: {result.stderr.strip()}")
        sys.exit(result.returncode)
    return result.stdout.strip()

def main():
    tag = os.environ.get("TAG")
    repo = os.environ.get("REPO")
    title = os.environ.get("TITLE", "")
    assets = os.environ.get("ASSETS")
    draft = os.environ.get("DRAFT", "").lower() == "true"

    if not tag or not repo or not assets:
        log_error("Required environment variables: TAG, REPO, ASSETS")
        sys.exit(1)

    prerelease_flag = "--prerelease" if is_prerelease(tag) else ""
    draft_flag = "--draft" if draft else ""
    title_arg = f'--title "{title or tag}"'

    log_info(f"Tag: {tag}")
    log_info(f"Repo: {repo}")
    log_info(f"Assets: {assets}")
    log_info(f"Draft: {draft}")
    log_info(f"Prerelease: {bool(prerelease_flag)}")
    log_info(f"Title: {title or tag}")

    create_cmd = f'gh release create "{tag}" --repo "{repo}" {prerelease_flag} {draft_flag} {title_arg}'
    run(create_cmd)
    log_success("GitHub release created.")

    for asset in assets.splitlines():
        asset = asset.strip()
        if asset:
            upload_cmd = f'gh release upload "{tag}" "{asset}" --repo "{repo}"'
            run(upload_cmd)
            log_success(f"Uploaded asset: {asset}")

main()
