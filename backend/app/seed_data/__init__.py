from .generator import generate_all

_store: dict = {}


def get_store() -> dict:
    return _store


def init_store() -> None:
    global _store
    _store = generate_all()
