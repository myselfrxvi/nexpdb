import uuid
from pathlib import Path
from typing import Any
from storage import StorageEngine

TYPE_MAP: dict[str, type] = {
    "INT": int,
    "TEXT": str
}

class TableManager:
    """Adds named tables, typed schemas, and row queries on top of StorageEngine."""
    def __init__(self, storage: StorageEngine):
        self.storage = storage
    def _get_schema(self, table: str) -> dict[str, str]:
        schema = self.storage.get(f"__schema__:{table}")
        if schema is None:
            raise ValueError(f"Table '{table}' doesn't exist.")
        return schema
