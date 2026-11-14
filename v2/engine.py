"""Deterministic game engine for the AI Escape Room (Version 2).

The engine is the single source of truth. It owns the game state and decides
whether every action succeeds. The LLM never changes the state: it only
(1) translates the player's text into an action and (2) narrates the result.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

CONFIG_PATH = Path(__file__).with_name("game_config.json")


def load_config(path: Path = CONFIG_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def new_state() -> dict:
    """Structured game state. Plain dict so it is easy to print, test and save."""
    return {
        "clues": [],            # clue ids the player has discovered
        "items_visible": [],    # items that are lying in the room, not yet taken
        "inventory": [],        # items the player carries
        "unlocked": [],         # lock ids that have been opened
        "escaped": False,
        "moves": 0,
        "failed_attempts": 0,
    }


def digits_only(text: str) -> str:
    return re.sub(r"\D", "", text or "")


def _norm(text: Optional[str]) -> str:
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", (text or "").lower()).split())


class GameEngine:
    def __init__(self, config: Optional[dict] = None, state: Optional[dict] = None):
        self.cfg = config or load_config()
        self.state = state or new_state()

    # ------------------------------------------------------------------ lookup
    def _match(self, name: Optional[str], table: dict) -> Optional[str]:
        """Resolve free text to an id using aliases (longest alias wins)."""
        text = f" {_norm(name)} "
        if text.strip() == "":
            return None
        best, best_len = None, 0
        for ident, entry in table.items():
            for alias in entry["aliases"]:
                if f" {_norm(alias)} " in text and len(alias) > best_len:
                    best, best_len = ident, len(alias)
        return best

    def resolve_object(self, name: Optional[str]) -> Optional[str]:
        return self._match(name, self.cfg["objects"])

    def resolve_item(self, name: Optional[str]) -> Optional[str]:
        return self._match(name, self.cfg["items"])

    def visible_objects(self) -> list[str]:
        out = []
        for oid, obj in self.cfg["objects"].items():
            req = obj.get("requires_clue")
            if req is None or req in self.state["clues"]:
                out.append(oid)
        return out

    def _lock_of(self, obj_id: str) -> Optional[tuple[str, dict]]:
        lock_id = self.cfg["objects"][obj_id].get("lock")
        return (lock_id, self.cfg["locks"][lock_id]) if lock_id else None

    def _item_name(self, item_id: str) -> str:
        return self.cfg["items"][item_id]["name"]

    # ------------------------------------------------------------------ results
    @staticmethod
    def _res(ok: bool, event: str, text: str, **extra: Any) -> dict:
        return {"ok": ok, "event": event, "text": text, **extra}

    def _add_clues(self, clue_ids: list[str]) -> list[str]:
        new = []
        for c in clue_ids:
            if c not in self.state["clues"]:
                self.state["clues"].append(c)
                new.append(c)
        return new

    # ------------------------------------------------------------------ main entry
    def handle(self, action: dict) -> dict:
        """Validate and apply one action. Returns a result dict for the narrator."""
        kind = str(action.get("action") or "unknown").lower()
        if self.state["escaped"]:
            return self._res(False, "already_escaped",
                             "You have already escaped the library. Press Restart to play again.")
        self.state["moves"] += 1
        handlers = {
            "look": lambda: self._look(),
            "examine": lambda: self._examine(action.get("target") or action.get("item")),
            "take": lambda: self._take(action.get("item") or action.get("target")),
            "use": lambda: self._use(action.get("item"), action.get("target")),
            "enter_code": lambda: self._enter_code(action.get("target"), action.get("code")),
            "open": lambda: self._open(action.get("target")),
            "inventory": lambda: self._inventory(),
            "hint": lambda: self._hint(),
            "help": lambda: self._help(),
        }
        handler = handlers.get(kind)
        if handler is None:
            return self._res(False, "invalid_action",
                             "That is not something you can do in this room. "
                             "You can look around, examine objects, take items, use items on objects, "
                             "enter codes, check your inventory or ask for a hint.")
        return handler()

    # ------------------------------------------------------------------ handlers
    def _look(self) -> dict:
        names = [self.cfg["objects"][o]["name"] for o in self.visible_objects()]
        text = "You are in the locked library. You can see: " + ", ".join(names) + "."
        loose = [self._item_name(i) for i in self.state["items_visible"]]
        if loose:
            text += " Lying within reach: " + ", ".join(loose) + "."
        return self._res(True, "look", text)

    def _examine(self, target: Optional[str]) -> dict:
        if not target:
            return self._res(False, "missing_target", "What do you want to examine?")
        item_id = self.resolve_item(target)
        if item_id and (item_id in self.state["inventory"] or item_id in self.state["items_visible"]):
            item = self.cfg["items"][item_id]
            new = self._add_clues(item.get("reveals_clues", []))
            return self._res(True, "examine_item", item["examine"],
                             new_clues=new, facts_digits=item.get("facts_digits"))
        obj_id = self.resolve_object(target)
        if obj_id and obj_id in self.visible_objects():
            obj = self.cfg["objects"][obj_id]
            lock = self._lock_of(obj_id)
            text = obj["examine"]
            if lock and lock[0] in self.state["unlocked"] and "examine_unlocked" in obj:
                text = obj["examine_unlocked"]
            new = self._add_clues(obj.get("reveals_clues", []))
            return self._res(True, "examine_object", text,
                             new_clues=new, facts_digits=obj.get("facts_digits"))
        return self._res(False, "not_found", f"There is no '{target}' here that you can examine.")

    def _take(self, name: Optional[str]) -> dict:
        if not name:
            return self._res(False, "missing_target", "What do you want to take?")
        item_id = self.resolve_item(name)
        if item_id and item_id in self.state["inventory"]:
            return self._res(False, "already_have", f"You are already carrying the {self._item_name(item_id)}.")
        if item_id and item_id in self.state["items_visible"]:
            self.state["items_visible"].remove(item_id)
            self.state["inventory"].append(item_id)
            return self._res(True, "take", self.cfg["items"][item_id]["take_text"], item=item_id)
        obj_id = self.resolve_object(name)
        if obj_id and obj_id in self.visible_objects():
            return self._res(False, "cannot_take", f"You cannot pick up the {self.cfg['objects'][obj_id]['name']}.")
        return self._res(False, "not_found", f"There is no '{name}' here that you can take.")

    def _use(self, item: Optional[str], target: Optional[str]) -> dict:
        if not item:
            return self._res(False, "missing_target", "Which item do you want to use?")
        item_id = self.resolve_item(item)
        # Same answer whether the item is hidden or does not exist: no information leak.
        if not item_id or item_id not in self.state["inventory"]:
            return self._res(False, "not_in_inventory", f"You are not carrying any '{item}'.")
        if not target:
            return self._res(False, "missing_target",
                             f"What do you want to use the {self._item_name(item_id)} on?")
        obj_id = self.resolve_object(target)
        if not obj_id or obj_id not in self.visible_objects():
            return self._res(False, "not_found", f"There is no '{target}' here to use that on.")
        lock = self._lock_of(obj_id)
        if not lock:
            return self._res(False, "no_effect", "Nothing happens.")
        lock_id, lock_cfg = lock
        if lock_id in self.state["unlocked"]:
            return self._res(False, "already_unlocked", "That is already open.")
        if lock_cfg["type"] == "item" and lock_cfg["item"] == item_id:
            return self._unlock(lock_id)
        self.state["failed_attempts"] += 1
        return self._res(False, "wrong_item", lock_cfg["wrong_text"])

    def _enter_code(self, target: Optional[str], code: Optional[str]) -> dict:
        entered = digits_only(str(code or ""))
        if not entered:
            return self._res(False, "missing_target", "Which code do you want to enter?")
        if not target:
            return self._res(False, "missing_target", "Where do you want to enter that code?")
        obj_id = self.resolve_object(target)
        if not obj_id or obj_id not in self.visible_objects():
            return self._res(False, "not_found", f"There is no '{target}' here to enter a code on.")
        lock = self._lock_of(obj_id)
        if not lock or lock[1]["type"] != "code":
            return self._res(False, "no_effect", "There is no dial or keypad on that.")
        lock_id, lock_cfg = lock
        if lock_id in self.state["unlocked"]:
            return self._res(False, "already_unlocked", "That is already open.")
        if entered == lock_cfg["code"]:
            return self._unlock(lock_id)
        self.state["failed_attempts"] += 1
        return self._res(False, "wrong_code", lock_cfg["wrong_text"])

    def _open(self, target: Optional[str]) -> dict:
        if not target:
            return self._res(False, "missing_target", "What do you want to open?")
        obj_id = self.resolve_object(target)
        if not obj_id or obj_id not in self.visible_objects():
            return self._res(False, "not_found", f"There is no '{target}' here to open.")
        lock = self._lock_of(obj_id)
        if not lock:
            return self._res(False, "no_effect", f"The {self.cfg['objects'][obj_id]['name']} cannot be opened.")
        lock_id, lock_cfg = lock
        if lock_id in self.state["unlocked"]:
            return self._res(False, "already_unlocked", "That is already open.")
        return self._res(False, "locked", lock_cfg["locked_text"])

    def _unlock(self, lock_id: str) -> dict:
        lock_cfg = self.cfg["locks"][lock_id]
        self.state["unlocked"].append(lock_id)
        for item_id in lock_cfg.get("reveals_items", []):
            if item_id not in self.state["items_visible"] and item_id not in self.state["inventory"]:
                self.state["items_visible"].append(item_id)
        if lock_cfg.get("win"):
            self.state["escaped"] = True
        return self._res(True, "unlocked", lock_cfg["unlock_text"], unlocked=lock_id)

    def _inventory(self) -> dict:
        inv = [self._item_name(i) for i in self.state["inventory"]]
        text = "You are carrying: " + ", ".join(inv) + "." if inv else "Your pockets are empty."
        return self._res(True, "inventory", text)

    def _hint(self) -> dict:
        for hint in self.cfg["hints"]:
            kind, _, ident = hint["until"].partition(":")
            done = (
                (kind == "clue" and ident in self.state["clues"])
                or (kind == "lock" and ident in self.state["unlocked"])
                or (kind == "item" and ident in self.state["inventory"])
            )
            if not done:
                return self._res(True, "hint", hint["text"])
        return self._res(True, "hint", "You have everything you need. Try the door.")

    def _help(self) -> dict:
        return self._res(True, "help", " ".join(i.replace("*", "") for i in self.cfg["instructions"][:3]))

    # ------------------------------------------------------------------ helpers for UI / LLM layer
    def clue_texts(self) -> list[str]:
        return [self.cfg["clues"][c] for c in self.state["clues"]]

    def inventory_names(self) -> list[str]:
        return [self._item_name(i) for i in self.state["inventory"]]

    def leaks_secret(self, text: str) -> bool:
        """True if `text` contains a code the player has not discovered yet."""
        d = digits_only(text)
        for secret in self.cfg["secrets"]:
            known = all(c in self.state["clues"] for c in secret["revealed_by"])
            if not known and secret["value"] in d:
                return True
        return False
