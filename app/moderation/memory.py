from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from app.utils.text import stable_hash


@dataclass
class MemoryCase:
    text_hash: str
    action: str
    reason: str
    source: str
    created_at: str


MEMORY: list[MemoryCase] = []


def remember_case(text: str, action: str, reason: str, source: str) -> None:
    MEMORY.append(
        MemoryCase(
            text_hash=stable_hash(text),
            action=action,
            reason=reason,
            source=source,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
    )


def recent_cases(limit: int = 20) -> list[dict[str, str]]:
    return [asdict(case) for case in MEMORY[-limit:]]
