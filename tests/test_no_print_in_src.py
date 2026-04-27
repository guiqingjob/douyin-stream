from __future__ import annotations

import re
from pathlib import Path


def test_no_print_in_src() -> None:
    root = Path(__file__).resolve().parents[1]
    src_root = root / "src" / "media_tools"

    pattern = re.compile(r"(?m)(^|[^\\w.])print\(")

    offenders: list[str] = []
    for path in src_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if pattern.search(text):
            offenders.append(str(path))

    assert offenders == []
