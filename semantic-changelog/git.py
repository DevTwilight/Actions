import subprocess
from typing import List, Dict, Optional
import logger

def run_git_command(args: List[str]) -> str:
    logger.print_info(f"Running git command: git {' '.join(args)}")
    try:
        result = subprocess.run(['git'] + args, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.print_error(f"Git command failed: {' '.join(args)}\n{e.stderr.strip()}")

def get_latest_tag() -> str:
    return run_git_command(['describe', '--tags', '--abbrev=0'])

def get_previous_tag(current_tag: str) -> Optional[str]:
    tags = run_git_command(['tag', '--sort=-creatordate']).split('\n')
    if current_tag not in tags:
        logger.print_warning(f"Current tag '{current_tag}' not found among tags.")
        return None
    index = tags.index(current_tag)
    if index + 1 < len(tags):
        return tags[index + 1]
    logger.print_warning(f"No previous tag found before '{current_tag}'.")
    return None

def get_commits(from_tag: Optional[str], to_tag: str) -> List[Dict[str, str]]:
    if from_tag:
        rev_range = f"{from_tag}..{to_tag}"
    else:
        rev_range = to_tag

    log_format = '%H|%s'
    log_output = run_git_command(['log', rev_range, '--pretty=format:' + log_format])
    if not log_output:
        return []

    commits = []
    for line in log_output.split('\n'):
        parts = line.split('|', 1)
        if len(parts) == 2:
            commits.append({
                "hash": parts[0],
                "message": parts[1].strip()
            })
    return commits
