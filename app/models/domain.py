"""Repository records. Dates use ISO 8601 UTC; IDs are positive integers."""
from dataclasses import dataclass, asdict
from typing import Literal

@dataclass
class Progress:
    topic_id: int
    state: Literal['not_started', 'in_progress', 'mastered'] = 'not_started'
    best_score: float | None = None
    latest_score: float | None = None

    def to_dict(self):
        return asdict(self)
