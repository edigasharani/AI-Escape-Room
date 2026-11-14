# 🔐 AI-Powered Escape Room

An interactive escape-room game in which a Large Language Model (Google Gemini) acts as the Game Master.
You wake up in a locked library and must examine objects, collect items, solve puzzles and enter the
right code to escape.

The repository contains **two versions** so the development process is visible:

||Version 1: simple|Version 2: reliable|
|-|-|-|
|Who runs the game?|The LLM, guided by a system prompt|Python engine; the LLM only parses input and narrates|
|Game state|Chat history only|Structured dict (inventory, clues, locks, escaped)|
|Rules and solutions|Inside the prompt|In `game\_config.json`, never sent to the LLM|
|Action validation|None (LLM decides)|Python functions per action|
|Adversarial inputs|Not handled (out of scope)|Handled and tested|
|Works without API key|No|Yes (rule-based fallback)|

## The problem

LLMs make great storytellers but unreliable referees. In a prompt-only game the model can forget solved puzzles,
invent objects, reveal clues too early, accept impossible actions (using a key you never picked up) or be talked
into unlocking the door ("I am the administrator..."). Version 2 shows how to keep the creativity of the LLM while
making the game logic deterministic and testable.

## The game

Objects: desk, bookshelf, painting, locked drawer, exit door (plus four red books once you inspect the shelf).
Puzzle chain: **books → drawer code → brass key → painting compartment → second half of door code → door.**

## Architecture

Diagrams for both versions are in [`docs/architecture.md`](docs/architecture.md).

```
v1/app.py            Streamlit UI + Gemini with a long system prompt
v2/game\_config.json  Objects, items, locks, codes, texts, hints, secrets
v2/engine.py         Game state + action validation (single source of truth)
v2/llm.py            Intent parser, guarded narrator, rule-based fallback
v2/app.py            Streamlit UI (inventory, journal, restart, developer mode)
tests/test\_v2.py     12 offline tests
docs/                Architecture, test cases, report, git workflow
```

## Technologies

Python 3.10+, [Streamlit](https://streamlit.io), [Google Gemini API](https://aistudio.google.com) via the `google-genai` SDK, `python-dotenv`, `pytest`.
No paid services are required; a free Gemini API key is enough.

## Install and run

```bash
git clone https://github.com/edigasharani/AI-Escape-Room.git
cd AI-Escape-Room
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt

cp .env.example .env             # Windows: copy .env.example .env
# edit .env and paste your key from https://aistudio.google.com/apikey

streamlit run v1/app.py          # Version 1
streamlit run v2/app.py          # Version 2
```

If your free tier does not offer the default model, set `GEMINI\_MODEL` in `.env` to one that it does.
Version 2 also runs **without** a key (rule-based parser and plain narration), which is handy for testing.

**Never commit your `.env` file.** It is listed in `.gitignore`.

## How Version 2 handles a turn

1. The **intent parser** turns "use the brass key on the painting" into `{"action":"use","item":"brass key","target":"painting"}`.
2. The **engine** validates it against the state and rules (is the key in the inventory? does it fit this lock?) and returns a result.
3. The **narrator** rewrites the result as atmospheric text. It never sees the player's raw message.
4. The **output guard** discards any narration that leaks an undiscovered code or loses required facts, and falls back to the engine text.

## Tests

```bash
python -m pytest -v
```

12 offline tests cover the assignment's challenge cases: uncollected key, wrong code, false "already solved" claim,
administrator impersonation and requests for all secrets. They also cover early clues, invented objects,
consistency, door bypass and a full playthrough. The comparison with Version 1 is in
[`docs/test\_cases.md`](docs/test_cases.md).

## Screenshots

*Add screenshots of V1 failures and V2 handling to `screenshots/` and link them here:*

```
!\[V1 accepting an admin request](screenshots/v1\_admin.png)
!\[V2 rejecting it](screenshots/v2\_admin.png)
```

## Limitations and future work

* The door code can be brute-forced; a lockout would fix that.
* State is lost on page reload.
* Free-text understanding of the rule-based fallback is keyword based.
* New rooms can be added by editing `game\_config.json` only.

## Report

See [`docs/report.md`](docs/report.md).

