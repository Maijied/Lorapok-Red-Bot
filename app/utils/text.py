import hashlib


def normalize_text(value: str) -> str:
    return " ".join(value.strip().split())


def stable_hash(value: str) -> str:
    normalized = normalize_text(value).encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()
