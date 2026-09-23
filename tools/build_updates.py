#!/usr/bin/env python3
"""Create updates.json from Markdown files in articles/."""
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
ARTICLES = ROOT / "articles"
OUTPUT = ROOT / "updates.json"
ALLOWED_TYPES = {"guide", "news", "video", "download"}
ALLOWED_CATEGORIES = {"articles", "tools"}


def parse_value(value):
    value = value.strip()
    if value.startswith('"') and value.endswith('"'):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1].replace("''", "'")
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    return value


def read_post(path):
    text = path.read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    try:
        end = next(index for index, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration:
        return None

    fields = {}
    for line in lines[1:end]:
        key, separator, value = line.partition(":")
        if separator:
            fields[key.strip().lower()] = parse_value(value)

    title = str(fields.get("title", "")).strip()
    if not title:
        return None
    kind = str(fields.get("type", "guide")).strip().lower()
    if kind not in ALLOWED_TYPES:
        kind = "guide"
    category = str(fields.get("category", "articles")).strip().lower()
    if category not in ALLOWED_CATEGORIES:
        category = "articles"
    date = str(fields.get("date", "")).strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        date = datetime.now(timezone.utc).date().isoformat()
    published = fields.get("published", True) is not False
    if not published:
        return None

    relative = path.relative_to(ROOT).as_posix()
    article_url = "https://github.com/hgn389/jxoffline/blob/main/" + quote(relative, safe="/")
    external_url = str(fields.get("url", "")).strip()
    if kind in ("video", "download") and external_url.startswith("https://"):
        article_url = external_url

    body_lines = lines[end + 1:]
    while body_lines and not body_lines[0].strip():
        body_lines.pop(0)
    if body_lines:
        first = body_lines[0].strip()
        if first.startswith("#") and first.lstrip("# ").strip().casefold() == title.casefold():
            body_lines.pop(0)
            while body_lines and not body_lines[0].strip():
                body_lines.pop(0)
    content = "\n".join(body_lines).strip()[:20000]
    summary = str(fields.get("summary", "")).strip()
    if not summary:
        for line in body_lines:
            if line.strip() and not line.lstrip().startswith(("#", "-", "*", ">", "```")):
                summary = line.strip()
                break

    return {
        "id": path.stem,
        "type": kind,
        "category": category,
        "title": title[:160],
        "summary": summary[:400],
        "date": date,
        "url": article_url,
        "content": content,
        "published": True,
        "pinned": fields.get("pinned", False) is True,
    }


def main():
    items = []
    for path in ARTICLES.rglob("*.md"):
        post = read_post(path)
        if post:
            items.append(post)
    items.sort(key=lambda post: post["date"], reverse=True)
    items.sort(key=lambda post: not post["pinned"])
    document = {
        "version": 1,
        "updated_at": datetime.now(timezone.utc).date().isoformat(),
        "items": items[:50],
    }
    OUTPUT.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
