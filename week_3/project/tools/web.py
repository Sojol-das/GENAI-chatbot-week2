import os
import re
import requests
from dotenv import load_dotenv

load_dotenv()

_SERPER_KEY = os.getenv("SERPER_API_KEY", "")
_SERPER_URL = "https://google.serper.dev/search"


def web_search(query: str, num_results: int = 5) -> str:
    if not _SERPER_KEY:
        return "[ERROR] SERPER_API_KEY not set in .env"
    try:
        resp = requests.post(
            _SERPER_URL,
            headers={"X-API-KEY": _SERPER_KEY, "Content-Type": "application/json"},
            json={"q": query, "num": num_results},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return f"[ERROR] web_search: {e}"

    lines = []
    box = data.get("answerBox", {}).get("answer") or data.get("answerBox", {}).get("snippet")
    if box:
        lines.append(f"[Answer] {box}\n")
    for item in data.get("organic", [])[:num_results]:
        lines.append(f"- {item.get('title', '')}\n  {item.get('link', '')}\n  {item.get('snippet', '')}")
    return "\n\n".join(lines) or "No results found."


def web_fetch(url: str, max_chars: int = 4000) -> str:
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (research-agent/1.0)"},
            timeout=12,
        )
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        return f"[ERROR] web_fetch: {e}"

    try:
        import trafilatura
        text = trafilatura.extract(html) or ""
    except ImportError:
        text = re.sub(r"<(script|style)[^>]*>.*?</(script|style)>", " ", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()

    return text[:max_chars] + ("…[truncated]" if len(text) > max_chars else "")
