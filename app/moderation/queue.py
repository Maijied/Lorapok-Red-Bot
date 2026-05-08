from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from uuid import uuid4


@dataclass
class ReviewCase:
    case_id: str
    text: str
    reason: str
    source: str
    status: str
    created_at: str
    reviewer_note: str = ""


REVIEW_QUEUE: list[ReviewCase] = []


def queue_case(text: str, reason: str, source: str) -> str:
    case = ReviewCase(
        case_id=str(uuid4()),
        text=text,
        reason=reason,
        source=source,
        status="pending",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    REVIEW_QUEUE.append(case)
    return case.case_id


def list_queue(status: str | None = None) -> list[dict[str, str]]:
    if status is None:
        return [asdict(case) for case in REVIEW_QUEUE]
    return [asdict(case) for case in REVIEW_QUEUE if case.status == status]


def resolve_case(case_id: str, status: str, reviewer_note: str = "") -> bool:
    if status not in {"approved", "rejected", "escalated"}:
        return False
    for case in REVIEW_QUEUE:
        if case.case_id == case_id:
            case.status = status
            case.reviewer_note = reviewer_note
            return True
    return False
