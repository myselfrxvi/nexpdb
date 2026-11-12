import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from storage import StorageEngine

TYPE_MAP: dict[str, type] = {
    "INT": int,
    "TEXT": str,
}


class TableManager:
    """Adds named tables, typed schemas, and row queries on top of StorageEngine."""

    def __init__(self, storage: StorageEngine) -> None:
        self.storage = storage

    def _get_schema(self, table: str) -> dict[str, str]:
        schema = self.storage.get(f"__schema__:{table}")
        if schema is None:
            raise ValueError(f"Table '{table}' doesn't exist.")
        return schema

    def _validate_row(self, schema: dict[str, str], row: dict[str, Any]) -> None:
        if set(row.keys()) != set(schema.keys()):
            raise ValueError(
                f"Columns mismatch: expected {list(schema.keys())}, got {list(row.keys())}"
            )
        for col, col_type in schema.items():
            expected = TYPE_MAP[col_type]
            val = row[col]
            # Note: bool is a subclass of int in Python, so reject True/False for INT
            if not isinstance(val, expected) or (expected is int and isinstance(val, bool)):
                raise ValueError(
                    f"Column '{col}' expects {col_type}, got {type(val).__name__}"
                )

    def _iter_table_rows(self, table: str) -> Iterator[tuple[str, dict[str, Any]]]:
        """Yield (storage_key, row_dict) pairs for every live row in `table`."""
        prefix = f"row:{table}:"
        for key in self.storage.keys():
            if key.startswith(prefix):
                row = self.storage.get(key)
                if row is not None:
                    yield key, row

    def create_table(self, name: str, columns: dict[str, str]) -> None:
        """Register a new table schema if it doesn't already exist."""
        if self.storage.get(f"__schema__:{name}") is not None:
            raise ValueError(f"Table '{name}' already exists.")

        for col, col_type in columns.items():
            if col_type not in TYPE_MAP:
                raise ValueError(
                    f"Unsupported column type: '{col_type}' for col '{col}'"
                )

        self.storage.set(f"__schema__:{name}", columns)

    def insert(self, table: str, row: dict[str, Any]) -> None:
        """Validate `row` against the table schema and persist it."""
        if not table:
            raise ValueError("Table name required.")

        schema = self._get_schema(table)
        self._validate_row(schema, row)
        key = f"row:{table}:{uuid.uuid4().hex[:12]}"
        self.storage.set(key, row)

    def select(
        self, table: str, where: tuple[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Return all rows in `table`, optionally filtered by `(column, value)`."""
        schema = self._get_schema(table)
        if where is not None:
            col, target = where
            if col not in schema:
                raise ValueError(f"Column '{col}' does not exist in table '{table}'.")
            return [row for _, row in self._iter_table_rows(table) if row.get(col) == target]

        return [row for _, row in self._iter_table_rows(table)]

    def delete_where(self, table: str, column: str, value: Any) -> int:
        """Delete all rows in `table` where `column == value`; return deleted count."""
        schema = self._get_schema(table)
        if column not in schema:
            raise ValueError(f"Column '{column}' does not exist in table '{table}'.")

        deleted = 0
        for key, row in self._iter_table_rows(table):
            if row.get(column) == value and self.storage.delete(key):
                deleted += 1
        return deleted


if __name__ == "__main__":
    test_file = Path("test_tables.ndb")
    test_file.unlink(missing_ok=True)

    engine = StorageEngine(str(test_file))
    db = TableManager(engine)

    # 1. Schema creation & duplicate guard
    db.create_table("users", {"id": "INT", "name": "TEXT"})
    db.create_table("orders", {"id": "INT", "item": "TEXT"})
    try:
        db.create_table("users", {"id": "INT"})
        assert False, "Should have rejected duplicate table"
    except ValueError:
        pass

    # 2. Insert valid rows & reject bad types / columns
    db.insert("users", {"id": 1, "name": "Alice"})
    db.insert("users", {"id": 2, "name": "Bob"})
    db.insert("orders", {"id": 1, "item": "Laptop"})
    try:
        db.insert("users", {"id": "not_an_int", "name": "Bad"})
        assert False, "Should have rejected wrong type"
    except ValueError:
        pass

    # 3. Select all and filtered (verifying tables don't collide)
    all_users = db.select("users")
    assert len(all_users) == 2, f"Expected 2 users, got {all_users}"
    only_bob = db.select("users", where=("id", 2))
    assert only_bob == [{"id": 2, "name": "Bob"}], f"Unexpected filter result: {only_bob}"
    assert db.select("orders") == [{"id": 1, "item": "Laptop"}], "Orders collided with users!"

    # 4. Delete where
    removed = db.delete_where("users", "name", "Alice")
    assert removed == 1, f"Expected 1 deleted row, got {removed}"
    assert db.select("users") == [{"id": 2, "name": "Bob"}]

    # 5. Restart persistence
    restarted = TableManager(StorageEngine(str(test_file)))
    assert restarted.select("users") == [{"id": 2, "name": "Bob"}]
    assert restarted.select("orders") == [{"id": 1, "item": "Laptop"}]

    test_file.unlink(missing_ok=True)
    print("ALL TABLE TESTS PASSED!")
