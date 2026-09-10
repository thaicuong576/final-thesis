"""Provider transport error types shared by atomic and composite paths."""

from __future__ import annotations

from typing import Sequence


class OpenAITransportError(RuntimeError):
    def __init__(self, blockers: Sequence[str]):
        self.blockers = tuple(blockers)
        super().__init__("openai transport failed")
