"""AI Escape Room - Version 2 (reliable): structured state + action validation.

Run:  streamlit run v2/app.py
"""
import streamlit as st
from dotenv import load_dotenv

from engine import GameEngine, load_config
from llm import GeminiClient, narrate, parse_intent

load_dotenv()
st.set_page_config(page_title="AI Escape Room v2", page_icon="🔐")


@st.cache_resource
def get_llm() -> GeminiClient:
    return GeminiClient()


def reset_game() -> None:
    cfg = load_config()
    st.session_state.engine = GameEngine(cfg)
    st.session_state.messages = [{"role": "assistant", "content": cfg["intro"], "debug": None}]


if "engine" not in st.session_state:
    reset_game()

engine: GameEngine = st.session_state.engine
llm = get_llm()
cfg = engine.cfg

# ----------------------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("🗒️ Game status")
    st.write(f"**Moves:** {engine.state['moves']}")
    st.write("**Inventory:** " + (", ".join(engine.inventory_names()) or "empty"))
    st.write("**Journal (clues found):**")
    clues = engine.clue_texts()
    if clues:
        for c in clues:
            st.markdown(f"- {c}")
    else:
        st.caption("Nothing yet.")
    st.divider()
    st.button("🔄 Restart game", on_click=reset_game, use_container_width=True)
    show_debug = st.checkbox("Developer mode (show parsed action and engine state)")
    st.caption("Mode: " + (f"Gemini ({llm.model})" if llm.enabled
                           else "offline (no API key: rule-based parser, plain narration)"))

# ----------------------------------------------------------------------------- main
st.title(f"🔐 {cfg['title']}")
with st.expander("How to play", expanded=len(st.session_state.messages) <= 1):
    for line in cfg["instructions"]:
        st.markdown(f"- {line}")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if show_debug and msg.get("debug"):
            st.json(msg["debug"], expanded=False)

if engine.state["escaped"]:
    st.success(f"🎉 You escaped in {engine.state['moves']} moves! Press Restart to play again.")

if prompt := st.chat_input("What do you do?", disabled=engine.state["escaped"]):
    st.session_state.messages.append({"role": "user", "content": prompt, "debug": None})
    action, parse_src = parse_intent(prompt, engine, llm)
    result = engine.handle(action)                       # Python decides what happens
    text, narr_src = narrate(result, action, engine, llm)  # LLM only describes it
    st.session_state.messages.append({
        "role": "assistant",
        "content": text,
        "debug": {"parsed_action": action, "parser": parse_src, "engine_result": result,
                  "narrator": narr_src, "state": engine.state},
    })
    st.rerun()
