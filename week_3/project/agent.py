"""
Research Desk — Week 3: Agent Memory & Persistent Sessions

Usage:
  python agent.py                        → interactive REPL
  python agent.py "your question"        → one-shot query
  python agent.py --tui                  → Textual TUI
  python agent.py --session <id>         → resume a session (REPL)
  python agent.py --session <id> "q"     → resume and ask once
"""
import os
import sys
import json
import uuid
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

from tools.web import web_search, web_fetch
from tools.papers import paper_search, read_paper
from tools.files import read_file, write_file, edit_file, list_files, set_workspace

load_dotenv()

# ── Config ─────────────────────────────────────────────────────────────────────
_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
_API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL = os.getenv("MODEL", "gemini-2.5-flash-lite")
MAX_ITERATIONS = 15

_HERE = Path(__file__).parent
SESSIONS_DIR = _HERE / ".agent" / "sessions"
WORKSPACE_ROOT = _HERE / "notes"

client = OpenAI(api_key=_API_KEY, base_url=_BASE_URL)
set_workspace(WORKSPACE_ROOT)

# ── Tool schemas (OpenAI function-calling format) ──────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current information, news, or facts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": "Fetch and read the text content of a webpage given its URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to fetch"},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "paper_search",
            "description": (
                "Search Hugging Face Papers (arXiv index) for ML/CS academic papers. "
                "Use this for research and literature questions, not web_search."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "description": "Max results (default 5)"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_paper",
            "description": (
                "Fetch the full text of an arXiv paper by its ID. "
                "Use arxiv_id from paper_search results — do not guess IDs."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "arxiv_id": {
                        "type": "string",
                        "description": "arXiv paper ID, e.g. '2305.18290'",
                    },
                },
                "required": ["arxiv_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file from the notes workspace with line numbers and optional pagination.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path relative to notes/"},
                    "start_line": {"type": "integer", "description": "First line to read (default 1)"},
                    "read_lines": {"type": "integer", "description": "Number of lines to read (default 200)"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or overwrite a file in the notes workspace. Use for new notes only; prefer edit_file for updates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path relative to notes/ (use lowercase-hyphenated names)"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": (
                "Edit an existing file with one of three operations: "
                "'replace' lines start_line–end_line with new content, "
                "'delete' lines start_line–end_line, "
                "'append' content after start_line (or at end if omitted). "
                "Returns a diff preview."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "operation": {"type": "string", "enum": ["replace", "delete", "append"]},
                    "start_line": {"type": "integer"},
                    "end_line": {"type": "integer"},
                    "content": {"type": "string"},
                },
                "required": ["path", "operation"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files in the notes workspace matching a glob pattern.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Glob pattern (default '**/*')"},
                },
                "required": [],
            },
        },
    },
]

TOOL_MAP = {
    "web_search": lambda a: web_search(**a),
    "web_fetch": lambda a: web_fetch(**a),
    "paper_search": lambda a: paper_search(**a),
    "read_paper": lambda a: read_paper(**a),
    "read_file": lambda a: read_file(**a),
    "write_file": lambda a: write_file(**a),
    "edit_file": lambda a: edit_file(**a),
    "list_files": lambda a: list_files(**a),
}

BASE_SYSTEM = "You are Research Desk, a helpful research assistant."

# ── Session management ──────────────────────────────────────────────────────────

def _sessions_dir() -> Path:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    return SESSIONS_DIR


def create_session() -> str:
    return uuid.uuid4().hex[:8]


def save_session(session_id: str, messages: list, title: str = None) -> None:
    path = _sessions_dir() / f"{session_id}.json"
    auto_title = title
    if not auto_title:
        for m in messages:
            if m.get("role") == "user" and isinstance(m.get("content"), str):
                auto_title = m["content"][:60]
                break
    data = {
        "id": session_id,
        "title": auto_title or "Untitled",
        "updated": datetime.now().isoformat(),
        "messages": messages,
    }
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_session(session_id: str) -> dict | None:
    path = _sessions_dir() / f"{session_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_sessions() -> list[dict]:
    sessions = []
    for f in sorted(_sessions_dir().glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            sessions.append({
                "id": data["id"],
                "title": data.get("title", ""),
                "updated": data.get("updated", ""),
            })
        except Exception:
            pass
    return sessions


def build_system_prompt(base: str) -> str:
    agents_md = _HERE / "AGENTS.md"
    if agents_md.exists():
        rules = agents_md.read_text(encoding="utf-8").strip()
        return base + "\n\n---\n\n" + rules
    return base


# ── Agent base class ────────────────────────────────────────────────────────────

class Agent:
    def __init__(self, session_id: str = None):
        WORKSPACE_ROOT.mkdir(exist_ok=True)
        system_text = build_system_prompt(BASE_SYSTEM)
        self.system_msg = {"role": "system", "content": system_text}

        if session_id:
            data = load_session(session_id)
            if data:
                self.session_id = session_id
                self.messages = data["messages"]
                self._emit(f"[Resumed session {session_id}: {data.get('title', '')}]")
            else:
                self._emit(f"[Session {session_id!r} not found — starting new session]")
                self.session_id = create_session()
                self.messages = []
        else:
            self.session_id = create_session()
            self.messages = []

    def _emit(self, text: str) -> None:
        """Output hook — override in subclasses to route tool logs."""
        pass

    def dispatch(self, name: str, args: dict) -> str:
        fn = TOOL_MAP.get(name)
        if fn is None:
            return f"[ERROR] Unknown tool: {name!r}"
        try:
            return str(fn(args))
        except Exception as e:
            return f"[ERROR] {name} failed: {e}"

    def _run_loop(self) -> str:
        for _ in range(MAX_ITERATIONS):
            response = client.chat.completions.create(
                model=MODEL,
                messages=[self.system_msg] + self.messages,
                tools=TOOLS,
                tool_choice="auto",
            )
            msg = response.choices[0].message
            self.messages.append(msg.model_dump(exclude_none=True))

            if not msg.tool_calls:
                save_session(self.session_id, self.messages)
                return msg.content or ""

            tool_results = []
            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments)
                self._emit(f"[tool] {tc.function.name}({json.dumps(args, ensure_ascii=False)[:120]})")
                result = self.dispatch(tc.function.name, args)
                self._emit(f"[result] {result[:300]}{'…' if len(result) > 300 else ''}")
                tool_results.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

            self.messages.extend(tool_results)
            save_session(self.session_id, self.messages)

        return "[ERROR] Max iterations reached."

    def chat(self, user_message: str) -> str:
        self.messages.append({"role": "user", "content": user_message})
        return self._run_loop()

    def run_once(self, question: str) -> str:
        return self.chat(question)


# ── REPLAgent ──────────────────────────────────────────────────────────────────

class REPLAgent(Agent):
    def _emit(self, text: str) -> None:
        print(text, file=sys.stderr)

    def run(self) -> None:
        print(f"Research Desk  [session {self.session_id}]")
        print("Type your question and press Enter. Ctrl+C or Ctrl+D to quit.\n")

        sessions = list_sessions()
        if sessions:
            print("Recent sessions:")
            for s in sessions[:5]:
                print(f"  {s['id']}  {s['title'][:60]}")
            print()

        try:
            while True:
                try:
                    question = input("You: ").strip()
                except EOFError:
                    break
                if not question:
                    continue
                answer = self.chat(question)
                print(f"\nAssistant: {answer}\n")
        except KeyboardInterrupt:
            print("\n[Goodbye]")


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    argv = sys.argv[1:]

    if "--tui" in argv:
        from tui import TUIAgent, ResearchDeskApp
        remaining = [a for a in argv if a != "--tui"]
        session_id = None
        if "--session" in remaining:
            idx = remaining.index("--session")
            if idx + 1 < len(remaining):
                session_id = remaining[idx + 1]
        agent = TUIAgent(session_id=session_id)
        ResearchDeskApp(agent).run()
        return

    session_id = None
    if "--session" in argv:
        idx = argv.index("--session")
        if idx + 1 < len(argv):
            session_id = argv[idx + 1]
            argv = [a for i, a in enumerate(argv) if i != idx and i != idx + 1]

    question = " ".join(a for a in argv if not a.startswith("--")).strip()

    if question:
        agent = REPLAgent(session_id=session_id)
        answer = agent.run_once(question)
        print(answer)
    else:
        agent = REPLAgent(session_id=session_id)
        agent.run()


if __name__ == "__main__":
    main()
