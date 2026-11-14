# Suggested Git workflow (meaningful history, no secrets)

The assignment asks for regular commits rather than one big final upload. Create the empty repository on
GitHub first (no README), then follow this order, committing as you actually build and test each part.
Adapt the messages to your own work.

```bash
git init -b main
git add .gitignore .env.example requirements.txt
git commit -m "chore: project skeleton, gitignore and env template"

git add v1/
git commit -m "feat(v1): Streamlit chat UI with Gemini as Game Master"

# run v1, try the adversarial cases, save screenshots
git add docs/test_cases.md screenshots/
git commit -m "docs(v1): record V1 failures with screenshots"

git add v2/game_config.json v2/engine.py
git commit -m "feat(v2): game config and deterministic engine with state and validation"

git add tests/
git commit -m "test(v2): offline tests for validation, consistency and adversarial inputs"

git add v2/llm.py v2/app.py
git commit -m "feat(v2): LLM intent parser, guarded narrator and Streamlit UI"

git add docs/architecture.md docs/report.md README.md
git commit -m "docs: architecture diagrams, report and README"

git remote add origin https://github.com/<your-username>/AI-Escape-Room.git
git push -u origin main
```

Before every commit run `git status` and make sure `.env` is not listed. If you ever commit a key by mistake,
revoke it at https://aistudio.google.com/apikey immediately; deleting the file in a later commit is not enough.
