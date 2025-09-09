import os
import re
import requests
import logger

def _get_issue_body(repo, token, issue_number):
    url = f"https://api.github.com/repos/{repo}/issues/{issue_number}"
    headers = {"Authorization": f"token {token}"} if token else {}
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        logger.print_warning(f"Failed to fetch issue #{issue_number} body: {r.status_code}")
        return ""
    data = r.json()
    return data.get("body", "")

def _get_mirrored_link(body):
    pattern = r"\[Mirrored from original issue\]\((https://github\.com/.+?/issues/\d+)\)"
    m = re.search(pattern, body)
    if not m:
        return None
    return m.group(1)

def _replace_refs(text, repo, token):
    def replacer(match):
        num = match.group(1)
        body = _get_issue_body(repo, token, num)
        mirrored = _get_mirrored_link(body)
        if mirrored:
            mirrored_parts = mirrored.rstrip('/').split('/')
            mirrored_num = mirrored_parts[-1]
            mirrored_repo = "/".join(mirrored_parts[-4:-2])
            return f"[#{mirrored_num}](https://github.com/{mirrored_repo}/issues/{mirrored_num})"
        else:
            return f"[#{num}](https://github.com/{repo}/issues/{num})"
    return re.sub(r"#(\d+)", replacer, text)

def parse_sections(raw):
    pairs = raw.split(",")
    sections = {}
    for p in pairs:
        if ":" not in p:
            continue
        key, val = p.split(":", 1)
        sections[key.strip()] = val.strip()
    return sections

def generate_changelog(commits, sections, template_path, tag, date, repo, token):
    entries = {k: [] for k in sections.keys()}
    seen = set()
    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()
    for commit in commits:
        msg = commit["message"]
        for prefix in sections.keys():
            pattern = f"^{re.escape(prefix)}\\s*:\\s*(.+)$"
            m = re.match(pattern, msg)
            if m:
                detail = m.group(1).strip()
                if detail in seen:
                    break
                seen.add(detail)
                detail = _replace_refs(detail, repo, token)
                entries[prefix].append(detail)
                break
    total = sum(len(v) for v in entries.values())
    if total == 0:
        logger.print_warning("No changelog entries matched section prefixes.")
        return ""

    lines = []

    for prefix, title in sections.items():
        if entries[prefix]:
            details = "\n".join(f"- {entry}" for entry in entries[prefix])
            section_text = (
                template
                .replace("{{VERSION}}", tag)
                .replace("{{DATE}}", date)
                .replace("{{CATEGORY}}", title)
                .replace("{{DETAIL}}", details)
            )
            section_lines = section_text.splitlines()
            if section_lines and section_lines[0].startswith("# "):
                section_lines = section_lines[1:]
            lines.extend(section_lines)
            lines.append("")
    return "\n".join(lines).strip()
