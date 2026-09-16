#!/usr/bin/env python3
"""Remove duplicate stylesheet links inserted after </head>."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP = {"backend", ".venv", "server_backup", "vidgenerator.backup", ".pytest-tmp", ".pytest_tmp"}
PAT = re.compile(
    r"</head>\s*(?:\s*<link rel=\"stylesheet\"[^>]+>\s*)+(?=<body>)",
    re.MULTILINE,
)


def main() -> None:
    fixed = 0
    for path in ROOT.rglob("index.html"):
        if any(part in SKIP for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        new = PAT.sub("</head>\n", text)
        if new != text:
            path.write_text(new, encoding="utf-8", newline="\n")
            fixed += 1
            print(path.relative_to(ROOT))
    print(f"Fixed {fixed} file(s).")


if __name__ == "__main__":
    main()
