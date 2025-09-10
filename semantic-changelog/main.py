import os
import sys
import datetime
import logger
import git
import changelog

def main():
    token = os.getenv("GITHUB_TOKEN")
    file_path = os.getenv("CHANGELOG_FILE")
    sections_raw = os.getenv("SECTIONS")
    template_path = os.getenv("TEMPLATE_FILE")
    tag = os.getenv("TAG")
    repo = os.getenv("GITHUB_REPOSITORY")
    github_output = os.getenv("GITHUB_OUTPUT")

    if not token:
        logger.print_error("GITHUB_TOKEN is required.")
    if not sections_raw:
        logger.print_error("SECTIONS input is required.")
    if not file_path:
        logger.print_error("CHANGELOG_FILE input is required.")
    if not template_path:
        logger.print_error("TEMPLATE_FILE input is required.")
    if not repo:
        logger.print_error("GITHUB_REPOSITORY environment variable is required.")

    if not tag:
        tag = git.get_latest_tag()
        if not tag:
            logger.print_error("No tag found and no TAG input provided.")

    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8-sig") as f:
            existing = f.read()
        if tag in existing:
            logger.print_warning(f"Changelog for tag {tag} already exists in {file_path}.")
            sys.exit(0)  
    if not os.path.isabs(template_path):
        action_dir = os.getenv('GITHUB_ACTION_PATH', '')
        if action_dir:
            template_path = os.path.join(action_dir, template_path)

    sections = changelog.parse_sections(sections_raw)

    previous_tag = git.get_previous_tag(tag)
    commits = git.get_commits(previous_tag, tag)
    commits.reverse()
    if not commits:
        logger.print_warning(f"No commits found between {previous_tag} and {tag}.")
        sys.exit(0)

    date = datetime.datetime.utcnow().strftime("%Y-%m-%d")

    changelog_content = changelog.generate_changelog(commits, sections, template_path, tag, date, repo, token)
    changelog_content = changelog_content.lstrip('\ufeff')

    if not changelog_content:
        logger.print_warning("No changelog content generated.")
        sys.exit(0)

    with open(file_path, "a", encoding="utf-8") as f:
        f.write("\n\n")
        f.write(changelog_content)
        f.write("\n")

    logger.print_success(f"Changelog updated in {file_path}")

    if github_output:
        with open(github_output, "a", encoding="utf-8") as out_file:
            out_file.write(f"tag={tag}\n")
    else:
        print(f"tag={tag}", flush=True)

if __name__ == "__main__":
    main()
