# AI-Powered Escape Room: Short Report

## 1. Goal

The project builds an interactive escape-room game in which a Large Language Model (Google Gemini) acts as the
Game Master. The player is locked in a library and must examine objects, collect items, solve puzzles and enter a
four-digit code to escape. The project has two versions: a simple prompt-only game (V1) and a reliable version
with structured state and validation (V2).

## 2. Game design

The room contains five interactive objects (desk, bookshelf, painting, drawer, door) and a hidden
sixth that appears only after investigation (the four red books). The solution is a chain of three puzzles:

1. **Books to drawer code.** Four crooked red books hide the numbers 2, 7, 1, 8. They open the drawer's combination lock (2718).
2. **Key to painting.** The drawer holds a brass key and a torn card ("4 7 _ _"). The key opens a compartment behind the painting, which holds a note ("the last two digits are 0 and 3").
3. **Final challenge.** The two halves are combined into the door code 4703.

The desk note ("Order matters on the shelf. What the painter hides needs something small and brass") works as a
soft hint for the chain.

## 3. Version 1: LLM as the whole game

**Implementation.** A Streamlit chat interface sends the full chat history to Gemini on every turn. A system prompt
describes the room, lists the secret solution and sets the rules. The game ends when the model outputs a special
`[[ESCAPED]]` token.

**Problems encountered.** The game works well when the player cooperates, but everything depends on the model
following text instructions:

- The only "state" is the conversation, so the model can forget a solved puzzle or contradict an earlier description.
- The solution is inside the prompt, so the player can ask for it and the model may reveal it.
- The model can accept impossible actions (using an uncollected key, claiming a puzzle is solved, "I am the administrator").
- The model can invent objects and reveal clues too early.
- **Observed in testing (Gemini `gemini-3.5-flash-lite`, 6 manual tests, screenshots in `screenshots/`):**
  - *Failed:* when I used a brass key I had never collected, V1 accepted it on the first try, opened the painting and revealed the note. It refused on the 3 later tries, so it failed in 1 of 4 attempts. The answer changed between identical inputs.
  - *Skipped a step:* asking to "examine the four books" before looking at the shelf showed the numbers 2, 7, 1, 8 immediately, because nothing enforces the order.
  - *Passed:* the fake administrator, the request for all secret codes, the false "I already opened the drawer" claim and the invented crystal ball were all refused.
  - Conclusion: V1 is not always wrong, but it is **inconsistent**. It behaves well when its prompt happens to cover a case and breaks otherwise, and nothing in code guarantees the rules.

## 4. Version 2: Python decides, the LLM describes

**Core idea.** Separate *deciding what happens* from *describing what happened*.

- **Game state** (`engine.py`): a dictionary with discovered clues, visible items, inventory, unlocked locks, moves and the escaped flag.
- **Game configuration** (`game_config.json`): objects, items, locks, codes, texts, hints and secrets. Solutions are never placed in any prompt.
- **Action validation**: the engine has one handler per action (examine, take, use, enter code, open, inventory, hint). Each checks the rules, for example that an item must be in the inventory, a lock must match, an object must be visible and a code must be exact. Failed actions return a clear reason and leave the state intact.
- **Intent parser**: Gemini (temperature 0) converts free text into a JSON action. Its prompt treats the message as data, and anything that is not a game action (authority claims, requests for secrets) becomes `unknown`. A code is accepted only if its digits really appear in the player's message.
- **Narrator**: Gemini rewrites the engine's result into atmospheric prose. It never sees the player's raw message, which removes the main prompt-injection path.
- **Output guard**: narration that contains an undiscovered code, or drops digits that the result requires, is replaced by the engine's own text.
- **Fallbacks**: without an API key, or when the API fails, a rule-based parser and plain engine text keep the game playable. This also makes the logic testable offline.

**Testing.** I ran the same six inputs against V2 in the app: all six were handled correctly (see `docs/test_cases.md`). In addition, twelve automated tests cover the five challenge cases from the assignment (uncollected key, wrong code,
false "already solved" claim, administrator impersonation, request for all secrets) plus early clues, invented
objects, consistency, door bypass and a full playthrough. All pass. See `docs/test_cases.md`.

## 5. Problems and lessons

- **Structured output from the LLM.** The model sometimes wraps JSON in code fences or invents fields, so the parser strips fences, validates the action name and falls back to rules on any error.
- **Information leaks through error messages.** Telling the player "that key is somewhere else" would reveal that it exists. The engine therefore gives the identical answer whether an item is hidden or non-existent.
- **Keyword parsing is brittle.** During testing the word "instructions" matched the help command when the input was "ignore previous instructions". Harmless, but it shows why the keyword fallback must only ever trigger safe actions.
- **Trade-off.** V2 is less free-form than V1: the player can only do what the engine supports. In exchange it is consistent, testable and robust.

## 6. Limitations and future work

- The door code can be brute-forced; a lockout after repeated failures would fix this.
- The narrator is instructed but not forced to report failures as failures.
- State is lost on page reload; it could be saved to a JSON file or database.
- More rooms could be added purely through `game_config.json`, since the engine is generic.
