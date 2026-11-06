"""Extension contract for later communication protocols.

V0.1 serialization supports ExecutionMessages only. New policies need a versioned
codec and must revisit exact solver state keys if their costs depend on history.
Counts are nonnegative integers; each message costs one credit.
"""
from typing import Protocol


class CommunicationCost(Protocol):
    def counts(self, token: int, seller: int, buyer: int) -> tuple[int, int]: ...
