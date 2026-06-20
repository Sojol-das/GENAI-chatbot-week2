import glob as _glob
import difflib
from pathlib import Path

WORKSPACE_ROOT: Path = Path("notes")


def set_workspace(root: Path) -> None:
    global WORKSPACE_ROOT
    WORKSPACE_ROOT = Path(root).resolve()
    WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)


def resolve_path(path: str) -> Path:
    p = (WORKSPACE_ROOT / path).resolve()
    root = WORKSPACE_ROOT.resolve()
    if not str(p).startswith(str(root)):
        raise ValueError(f"Path {path!r} escapes workspace")
    return p


def read_file(path: str, start_line: int = 1, read_lines: int = 200) -> str:
    try:
        p = resolve_path(path)
        lines = p.read_text(encoding="utf-8").splitlines()
    except ValueError as e:
        return f"[ERROR] {e}"
    except FileNotFoundError:
        return f"[ERROR] File not found: {path}"
    except Exception as e:
        return f"[ERROR] read_file: {e}"

    start = max(0, start_line - 1)
    chunk = lines[start : start + read_lines]
    numbered = "\n".join(f"{i + start + 1:4}| {line}" for i, line in enumerate(chunk))
    remaining = len(lines) - start - read_lines
    suffix = f"\n[... {remaining} more lines]" if remaining > 0 else ""
    return numbered + suffix


def write_file(path: str, content: str) -> str:
    try:
        p = resolve_path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Wrote {len(content)} chars to {path}"
    except ValueError as e:
        return f"[ERROR] {e}"
    except Exception as e:
        return f"[ERROR] write_file: {e}"


def edit_file(
    path: str,
    operation: str,
    start_line: int = None,
    end_line: int = None,
    content: str = "",
) -> str:
    try:
        p = resolve_path(path)
        original = p.read_text(encoding="utf-8").splitlines(keepends=True)
        lines = list(original)
    except ValueError as e:
        return f"[ERROR] {e}"
    except FileNotFoundError:
        if operation == "append":
            lines = []
            original = []
            p = resolve_path(path)
        else:
            return f"[ERROR] File not found: {path}"
    except Exception as e:
        return f"[ERROR] edit_file: {e}"

    def _ensure_newline(text: str) -> list[str]:
        return [(l if l.endswith("\n") else l + "\n") for l in (text or "").splitlines()]

    if operation == "replace":
        s = (start_line or 1) - 1
        e = (end_line or start_line or 1) - 1
        lines[s : e + 1] = _ensure_newline(content)
    elif operation == "delete":
        s = (start_line or 1) - 1
        e = (end_line or start_line or 1) - 1
        lines[s : e + 1] = []
    elif operation == "append":
        after = start_line if start_line is not None else len(lines)
        lines[after:after] = _ensure_newline(content)
    else:
        return f"[ERROR] Unknown operation: {operation!r}. Use replace, delete, or append."

    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("".join(lines), encoding="utf-8")
    except Exception as e:
        return f"[ERROR] edit_file write: {e}"

    diff = list(difflib.unified_diff(original, lines, fromfile=f"a/{path}", tofile=f"b/{path}", lineterm=""))
    diff_str = "\n".join(diff[:30]) + ("\n[diff truncated]" if len(diff) > 30 else "")
    return f"[edit ok]\n{diff_str}" if diff_str else "[edit ok, no changes]"


def list_files(pattern: str = "**/*") -> str:
    try:
        root = WORKSPACE_ROOT.resolve()
        matches = [
            str(Path(m).relative_to(root))
            for m in _glob.glob(str(root / pattern), recursive=True)
            if Path(m).is_file()
        ]
    except Exception as e:
        return f"[ERROR] list_files: {e}"

    return "\n".join(sorted(matches)) or "(no files found)"
