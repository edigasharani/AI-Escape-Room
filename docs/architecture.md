# Architecture

GitHub renders the Mermaid diagrams below automatically.

## Version 1: the LLM is the whole game

```mermaid
flowchart LR
    P([Player]) -->|natural-language message| UI[Streamlit chat UI]
    UI -->|full chat history + message| LLM[Gemini<br/>Game Master]
    SP[/System prompt:<br/>room, clues, solution, rules/] --> LLM
    LLM -->|narration<br/>+ ESCAPED token| UI
    UI -->|display| P
    UI <--> H[(Chat history<br/>st.session_state)]
```

**Weakness:** the rules, the solution and the "memory" all live in text that the LLM can ignore, forget or leak.
The only game state is the chat history, and the only win check is a token the LLM chooses to emit.

## Version 2: Python decides, the LLM describes

```mermaid
flowchart LR
    P([Player]) -->|message| UI[Streamlit chat UI]
    UI --> IP["Intent parser<br/>(Gemini, temperature 0)<br/>fallback: rule-based"]
    IP -->|"JSON action<br/>{action, target, item, code}"| ENG
    subgraph PY [Python: single source of truth]
        ENG["Game engine<br/>action validation"] <--> ST[("Game state<br/>inventory, clues,<br/>unlocked, escaped")]
        CFG[/"game_config.json<br/>objects, items, locks,<br/>secrets, hints"/] --> ENG
    end
    ENG -->|"result (ground truth)"| NAR["Narrator<br/>(Gemini)<br/>never sees player text"]
    NAR -->|draft narration| GRD{"Output guard<br/>no leaked codes,<br/>facts preserved"}
    GRD -->|safe| UI
    GRD -->|unsafe| FB["Use engine's<br/>canonical text"] --> UI
    UI -->|display + sidebar from state| P
```

## Key design decisions

| Concern | Decision |
|---|---|
| Who decides success? | `engine.py` only. LLM output never modifies the state. |
| Where are solutions stored? | `game_config.json`. They are never inserted into any prompt. |
| Prompt injection | The intent parser can only output a fixed JSON schema; authority claims and demands become `unknown`. The narrator never sees the player's raw message. |
| Hallucinated codes and objects | A code must literally appear in the player's text; objects must resolve to ids in the config. |
| Leaks | `leaks_secret()` blocks any narration containing an undiscovered code. |
| API down or no key | The rule-based parser and the engine's canonical text keep the game playable. |
