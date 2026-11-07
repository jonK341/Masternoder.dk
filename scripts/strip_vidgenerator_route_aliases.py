"""
Remove duplicate /vidgenerator/api route aliases from backend/routes.

Keeps all_page_routes.py redirect handlers. Run: python scripts/strip_vidgenerator_route_aliases.py
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROUTES = ROOT / "backend" / "routes"
SKIP_FILES = frozenset({"all_page_routes.py", "vidgenerator_disabled_routes.py"})
ROUTE_PATH = re.compile(r"route\(\s*(['\"])([^'\"]+)\1")


def canonical(path: str) -> str:
    if path.startswith("/vidgenerator/api/"):
        return "/api/" + path[len("/vidgenerator/api/") :]
    if path in ("/vidgenerator", "/vidgenerator/"):
        return "/"
    if path.startswith("/vidgenerator/"):
        return "/" + path[len("/vidgenerator/") :]
    return path


def rewrite_route_line(line: str, new_path: str) -> str:
    return ROUTE_PATH.sub(lambda m: f"route({m.group(1)}{new_path}{m.group(1)}", line, count=1)


def process_block(block_lines: list[str]) -> tuple[list[str], bool]:
    paths: list[str | None] = []
    for line in block_lines:
        m = ROUTE_PATH.search(line)
        paths.append(m.group(2) if m else None)

    non_legacy = {p for p in paths if p and not p.startswith("/vidgenerator")}
    out: list[str] = []
    changed = False
    for line, path in zip(block_lines, paths):
        if not path or not path.startswith("/vidgenerator"):
            out.append(line)
            continue
        canon = canonical(path)
        if canon in non_legacy:
            changed = True
            continue
        if canon != path:
            out.append(rewrite_route_line(line, canon))
            changed = True
        else:
            out.append(line)
    return out, changed


def drop_vid_shim(lines: list[str]) -> tuple[list[str], bool]:
    """Remove def foo_vid(): return foo() shims."""
    out: list[str] = []
    changed = False
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"(\s*)def\s+(\w+_vid)\s*\([^)]*\)\s*:\s*$", line)
        if m:
            body = lines[i + 1] if i + 1 < len(lines) else ""
            if re.match(r"\s*return\s+\w+\(\)\s*$", body.strip()):
                changed = True
                i += 2
                while i < len(lines) and lines[i].strip() == "":
                    i += 1
                continue
        out.append(line)
        i += 1
    return out, changed


def process_file(path: Path) -> bool:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    out: list[str] = []
    changed = False
    i = 0
    while i < len(lines):
        if lines[i].lstrip().startswith("@") and ".route(" in lines[i]:
            block: list[str] = []
            while i < len(lines) and lines[i].lstrip().startswith("@") and ".route(" in lines[i]:
                block.append(lines[i])
                i += 1
            processed, block_changed = process_block(block)
            changed |= block_changed
            out.extend(processed)
            continue
        out.append(lines[i])
        i += 1

    out, shim_changed = drop_vid_shim(out)
    changed |= shim_changed

    if changed:
        path.write_text("".join(out), encoding="utf-8")
    return changed


def main():
    touched = 0
    for py in sorted(ROUTES.glob("*.py")):
        if py.name in SKIP_FILES:
            continue
        text = py.read_text(encoding="utf-8", errors="ignore")
        if "/vidgenerator" not in text:
            continue
        if process_file(py):
            touched += 1
            print("updated", py.relative_to(ROOT))
    print("files updated:", touched)


if __name__ == "__main__":
    main()
