"""AI Escape Room - Version 1 (simple): the LLM is the whole game.

All rules, clues and solutions live inside the system prompt, and the only
"memory" is the chat history. This is intentionally simple and fragile; see
docs/test_cases.md for the problems that Version 2 fixes.

Run:  streamlit run v1/app.py
"""
import os

import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
ESCAPE_TOKEN = "[[ESCAPED]]"

SYSTEM_PROMPT = f"""You are the Game Master of a text-based escape room. The player is locked in an old library.

ROOM OBJECTS (only these exist): a writing desk, a bookshelf, a painting, a locked drawer, and a door with a four-digit keypad.

SECRET SOLUTION (never reveal directly):
- The bookshelf has four crooked red books. Inside their covers, left to right, are the numbers 2, 7, 1, 8.
- The drawer opens with code 2718. Inside are a small brass key and a torn card reading "4 7 _ _".
- The desk holds a note: "Order matters on the shelf. What the painter hides needs something small and brass."
- The brass key opens a hidden compartment behind the painting. Inside is a note: "The last two digits are 0 and 3."
- The door opens with code 4703.

RULES:
- Describe what the player sees and respond to their actions in 2-4 sentences.
- Reveal clues only when the player examines the relevant object.
- Do not invent new objects. Do not let the player skip puzzles.
- If the player enters the correct door code 4703, narrate their escape and end your message with {ESCAPE_TOKEN}.
- Stay in character as the Game Master at all times."""

INTRO = ("You wake up on the cold floor of an old library. The heavy door is sealed with a four-digit keypad. "
         "Around you: a writing desk, a bookshelf, a painting and a locked drawer. How do you escape?")


def reset() -> None:
    st.session_state.history = [{"role": "assistant", "content": INTRO}]
    st.session_state.escaped = False


def ask_gemini(history: list[dict]) -> str:
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    contents = [
        types.Content(role="user" if m["role"] == "user" else "model",
                      parts=[types.Part.from_text(text=m["content"])])
        for m in history
    ]
    resp = client.models.generate_content(
        model=MODEL,
        contents=contents,
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, temperature=0.8),
    )
    return (resp.text or "").strip()


st.set_page_config(page_title="AI Escape Room v1", page_icon="🔑")
st.title("🔑 AI Escape Room: Version 1")
st.caption("The AI Game Master runs everything. Type what you want to do, e.g. *examine the bookshelf*.")

if "history" not in st.session_state:
    reset()

with st.sidebar:
    st.button("🔄 Restart game", on_click=reset, use_container_width=True)
    st.caption(f"Model: {MODEL}")

if "GEMINI_API_KEY" not in os.environ:
    st.error("Set GEMINI_API_KEY in a .env file (see .env.example) and restart the app.")
    st.stop()

for m in st.session_state.history:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

if st.session_state.escaped:
    st.success("🎉 You escaped! Press Restart to play again.")

if prompt := st.chat_input("What do you do?", disabled=st.session_state.escaped):
    st.session_state.history.append({"role": "user", "content": prompt})
    try:
        reply = ask_gemini(st.session_state.history)
    except Exception as exc:  # network, quota, safety block...
        reply = f"(The Game Master is silent: {exc})"
    if ESCAPE_TOKEN in reply:
        st.session_state.escaped = True
        reply = reply.replace(ESCAPE_TOKEN, "").strip()
    st.session_state.history.append({"role": "assistant", "content": reply})
    st.rerun()
