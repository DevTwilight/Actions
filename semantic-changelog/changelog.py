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

    # Replace global placeholders
    template = template.replace("{{VERSION}}", tag).replace("{{DATE}}", date)

    template_lines = template.splitlines()
    header_line = ""
    body_template = template

    if template_lines and template_lines[0].startswith("# "):
        header_line = template_lines[0]
        body_template = "\n".join(template_lines[1:])
    else:
        header_line = f"## {tag} - {date}"

    lines = [header_line, ""]

    for prefix, title in sections.items():
        if entries[prefix]:
            lines.append(f"### {title}")
            for entry in entries[prefix]:
                entry_text = body_template.replace("{{CATEGORY}}", title).replace("{{DETAIL}}", entry)
                lines.append(entry_text)
            lines.append("")

    return "\n".join(lines).strip()
