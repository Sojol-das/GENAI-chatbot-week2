import os
import requests
from dotenv import load_dotenv

load_dotenv()

_HF_TOKEN = os.getenv("HF_TOKEN", "")
_HF_SEARCH = "https://huggingface.co/api/papers/search"
_HF_PAPER = "https://huggingface.co/api/papers/{arxiv_id}"


def _headers() -> dict:
    h = {"Accept": "application/json"}
    if _HF_TOKEN:
        h["Authorization"] = f"Bearer {_HF_TOKEN}"
    return h


def paper_search(query: str, limit: int = 5) -> str:
    try:
        resp = requests.get(
            _HF_SEARCH,
            params={"q": query, "limit": limit},
            headers=_headers(),
            timeout=12,
        )
        resp.raise_for_status()
        papers = resp.json()
    except Exception as e:
        return f"[ERROR] paper_search: {e}"

    if not papers:
        return "No papers found."

    lines = []
    for p in papers[:limit]:
        arxiv_id = p.get("id", "")
        title = p.get("title", "Unknown")
        abstract = (p.get("abstract") or p.get("summary") or "")[:300]
        lines.append(f"- {title}\n  arxiv_id: {arxiv_id}\n  {abstract}")
    return "\n\n".join(lines)


def read_paper(arxiv_id: str, max_chars: int = 8000) -> str:
    # Normalize: strip URL prefixes and version suffixes cautiously
    arxiv_id = arxiv_id.strip()
    for prefix in ("https://arxiv.org/abs/", "http://arxiv.org/abs/", "arxiv.org/abs/"):
        if arxiv_id.startswith(prefix):
            arxiv_id = arxiv_id[len(prefix):]

    try:
        url = _HF_PAPER.format(arxiv_id=arxiv_id)
        resp = requests.get(url, headers=_headers(), timeout=12)
        if resp.status_code == 404:
            return (
                f"[404] Paper {arxiv_id!r} is not indexed on HF Papers. "
                f"Try: web_fetch('https://arxiv.org/abs/{arxiv_id}')"
            )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return f"[ERROR] read_paper: {e}"

    title = data.get("title", "")
    summary = data.get("summary") or data.get("abstract") or ""
    content = data.get("content") or ""
    paper_url = f"https://arxiv.org/abs/{arxiv_id}"

    out = f"# {title}\narxiv: {paper_url}\n\n## Abstract\n{summary}\n\n## Content\n{content}"
    return out[:max_chars] + ("…[truncated]" if len(out) > max_chars else "")
