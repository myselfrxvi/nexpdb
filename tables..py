from multiprocessing.sharedctypes import Value
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
    
    def _validate_row(self, schema: dict[str, str], row: dict[str, Any])-> None:
        if set(row.keys()) != set(schema.keys()):
            raise ValueError(
                f"Columns mismatch: expected {list(schema.keys())}"
            )
        for col, col_type in schema.items():
            expected = TYPE_MAP[col_type]
            val = row[col]
            if not isinstance(val,expected) or (expected is int and isinstance(val, bool)):
                raise ValueError(
                    f"Column '{col}' expects {col_type}, got {type(val).__name___}"
                )

    def create_table(self, name: str, columns: dict[str, str]):
        """Register