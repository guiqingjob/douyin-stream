"""Transcript preview extraction shared by orchestrator and local-transcribe worker."""
from pathlib import Path

PREVIEW_CHARS = 200


def extract_transcript_preview(file_path: Path | str, max_chars: int = PREVIEW_CHARS) -> str:
    """Read first meaningful prose from a transcript markdown file.

    Skips leading whitespace, YAML frontmatter, and '# heading' lines.
    Returns up to max_chars characters, single-spaced.
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

    body = " ".join(line.strip() for line in lines[i:] if line.strip())
    if len(body) > max_chars:
        body = body[:max_chars].rstrip() + "…"
    return body
