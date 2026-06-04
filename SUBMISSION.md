# CSOT Week 1 — Terminal Chatbot (Gemini)

Multi-turn terminal chatbot demonstrating:
- Gemini API integration via `google-generativeai`
- API key hygiene with `.env` + `python-dotenv`
- Manual conversation history management (the core of all agents)

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create your .env file (copy the template)
cp .env.example .env

# 3. Add your actual Gemini API key to .env
#    Get one free at: https://aistudio.google.com/app/apikey

# 4. Run
python chatbot.py
```

## Key Concepts

### Why conversation_history matters

The Gemini API (like all LLM APIs) is **stateless** — each call is independent.
The model has no memory of what you said before unless you send it yourself.

`conversation_history` is a Python list of dicts:
```python
[
    {"role": "user",  "parts": ["What is gradient descent?"]},
    {"role": "model", "parts": ["Gradient descent is ..."]},
    {"role": "user",  "parts": ["Give me a Python example"]},
    # ↑ full list sent on every API call
]
```

Every turn: append user message → call API with full list → append model reply → loop.

### API Key Safety

- Keys live in `.env` — never in source code
- `.gitignore` blocks `.env` from git commits
- `.env.example` is committed as a template (no real key in it)
- `os.getenv("GEMINI_API_KEY")` reads it at runtime

## Commands in the chatbot

| Command   | Effect                              |
|-----------|-------------------------------------|
| `history` | Shows number of turns in memory     |
| `clear`   | Resets conversation from scratch    |
| `quit`    | Exits the program                   |
