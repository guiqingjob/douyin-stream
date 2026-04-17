"""Transcript preview + full-text extraction shared by orchestrator and local-transcribe worker."""
from pathlib import Path

PREVIEW_CHARS = 200


def _read_body(file_path: Path | str) -> str:
    """Read a transcript markdown file and return the prose body only.

    Strips YAML frontmatter and leading '#'-headings + blank lines. Remaining
    lines are single-spaced into one string.
    """
    try:
        text = Path(file_path).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""

    lines = text.splitlines()
    i = 0
    # Skip YAML frontmatter
    if lines and lines[0].strip() == "---":
        i = 1
        while i < len(lines) and lines[i].strip() != "---":
            i += 1
        i += 1
    # Skip blank + heading lines
    while i < len(lines) and (not lines[i].strip() or lines[i].lstrip().startswith("#")):
        i += 1

    return " ".join(line.strip() for line in lines[i:] if line.strip())


def extract_transcript_preview(file_path: Path | str, max_chars: int = PREVIEW_CHARS) -> str:
    """Return the first ~max_chars of the transcript body (for card previews)."""
    body = _read_body(file_path)
    if len(body) > max_chars:
        body = body[:max_chars].rstrip() + "…"
    return body


def extract_transcript_text(file_path: Path | str) -> str:
    """Return the full transcript body (for DB-backed search)."""
    return _read_body(file_path)
