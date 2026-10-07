"""
NIA — ConversationMemory (short-term turn buffer)

Inspired by: OpenYabby's session-history.js + getOrCreateAgentConversation()

Stores the last N turns of conversation per user_id so the Planner can
send conversation history to the LLM without the Android app needing to
re-send the full history on every request.

This is separate from MemoryService (long-term facts). ConversationMemory:
  - Is ephemeral (in-process; lost on restart — use a real DB in production)
  - Stores only { role, content } pairs, not raw Android request objects
  - Caps at MAX_TURNS per user to bound token usage
  - Never stores tool results verbatim — only the final spoken response

Design principle: the Android app sends its transcript; the backend maintains
the turn history. The Android app does NOT need to re-send history every time.
"""
from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, List, Optional

logger = logging.getLogger("nia.memory.conversation")

# Maximum turns to keep per user. Each turn = { role, content }.
# 6 turns = 3 full exchanges = ~1500 tokens at average verbosity.
MAX_TURNS = 12


@dataclass
class Turn:
    role: str    # "user" | "assistant"
    content: str


class ConversationMemory:
    """
    Per-user short-term conversation history.

    Thread-safety: NOT thread-safe. FastAPI runs in a single async event loop;
    this is safe as long as no CPU-bound parallel access occurs.
    Replace with Redis or a DB in a multi-process deployment.
    """

    def __init__(self, max_turns: int = MAX_TURNS) -> None:
        self._max_turns = max_turns
        # { user_id -> deque[Turn] }
        self._history: Dict[str, Deque[Turn]] = {}

    def add_turn(self, user_id: str, role: str, content: str) -> None:
        """
        Append a turn for user_id. Automatically evicts oldest when over the cap.

        Args:
          user_id:  device-id or session token from X-Device-Id header
          role:     "user" or "assistant"
          content:  the message text
        """
        if not content or not content.strip():
            return
        turns = self._history.setdefault(user_id, deque(maxlen=self._max_turns))
        turns.append(Turn(role=role, content=content.strip()))

    def get_history(
        self,
        user_id: str,
        last_n: Optional[int] = None,
    ) -> List[Dict[str, str]]:
        """
        Return the conversation history as a list of { role, content } dicts,
        ready to pass to the LLM provider.

        Args:
          user_id:  device-id
          last_n:   if set, return only the most recent last_n turns
        """
        turns = list(self._history.get(user_id, []))
        if last_n is not None:
            turns = turns[-last_n:]
        return [{"role": t.role, "content": t.content} for t in turns]

    def clear(self, user_id: str) -> int:
        """
        Delete all turns for user_id. Returns the number of turns deleted.
        Called when the user resets the conversation.
        """
        turns = self._history.pop(user_id, deque())
        count = len(turns)
        logger.info("CONVERSATION cleared user=%s turns=%d", user_id, count)
        return count

    def turn_count(self, user_id: str) -> int:
        return len(self._history.get(user_id, []))


# Module-level singleton — shared across all requests in one process
conversation_memory = ConversationMemory()
