# Week 3 Submission — Research Desk

## What I built

A full research agent with persistent memory, academic paper search, and file tools — runnable as an interactive REPL, one-shot CLI, or Textual TUI.

## Architecture decisions

**Agent class hierarchy**
All loop logic, tool dispatch, and session I/O live in the `Agent` base class. `REPLAgent` and `TUIAgent` only override `_emit()` and `run()`. This keeps the brain completely decoupled from the interface — swapping the UI requires zero changes to agent logic.

**Session persistence**
Conversations are saved as JSON files in `.agent/sessions/` after every tool round-trip. Each session has a short hex ID so users can resume with `--session <id>`. The session title is auto-derived from the first user message.

**AGENTS.md procedural memory**
Rules are loaded from `AGENTS.md` and prepended to the system prompt at startup. This makes behaviour easy to tweak without touching code — the same pattern used by production coding agents.

**File tools sandboxed to `notes/`**
All file operations resolve paths relative to `notes/` and reject any path that escapes the workspace. `edit_file` returns a unified diff preview so the model can verify its own edits. Line-numbered output in `read_file` lets the model target specific lines precisely.

**HuggingFace Papers API over AlphaXiv MCP**
The HF Papers API is a direct HTTP call — no MCP server to manage. `paper_search` uses hybrid semantic + full-text search; `read_paper` fetches full content only when needed to save tokens. 404s fall back gracefully to `web_fetch` on arxiv.org.

## Tools registered (8 total)

| Tool | Purpose |
|------|---------|
| `web_search` | Serper API web search |
| `web_fetch` | Fetch + extract page text (trafilatura) |
| `paper_search` | HF Papers semantic search |
| `read_paper` | Fetch full arXiv paper content |
| `read_file` | Paginated, line-numbered file read |
| `write_file` | Create new note files |
| `edit_file` | replace / delete / append with diff preview |
| `list_files` | Glob-based file listing |

## Usage

```bash
python agent.py                     # interactive REPL
python agent.py "your question"     # one-shot
python agent.py --tui               # Textual TUI
python agent.py --session <id>      # resume session
```
