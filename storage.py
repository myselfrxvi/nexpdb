import json
from pathlib import Path
from typing import Any


class StorageEngine:
    """Append-only log storage engine with an in-memory byte-offset index."""

    def __init__(self, filepath: str) -> None:
        self.path = Path(filepath)
        self._index: dict[str, int] = {}  # key -> byte offset of latest record
        self._load_index()

    def _load_index(self) -> None:
        """Rebuild the in-memory index by replaying the log file from byte 0."""
        if not self.path.exists():
            return

        with open(self.path, "rb") as f:
            while True:
                offset = f.tell()  # Capture position before reading the line
                line = f.readline()
                if not line:
                    break

                record = json.loads(line.decode("utf-8"))
                if record["op"] == "set":
                    self._index[record["key"]] = offset
                elif record["op"] == "del":
                    self._index.pop(record["key"], None)

    def _append_record(self, record: dict[str, Any]) -> int:
        """Append one JSON-line record to disk and return its starting byte offset."""
        data = (json.dumps(record) + "\n").encode("utf-8")
        with open(self.path, "ab") as f:
            f.seek(0, 2)  # Ensure cursor is at EOF before reading offset
            offset = f.tell()
            f.write(data)
        return offset

    def set(self, key: str, value: Any) -> None:
        """Persist a key-value pair and point the index to the new byte offset."""
        offset = self._append_record({"op": "set", "key": key, "val": value})
        self._index[key] = offset

    def get(self, key: str) -> Any | None:
        """Fetch the latest value for a key using a direct O(1) file seek."""
        offset = self._index.get(key)
        if offset is None:
            return None

        with open(self.path, "rb") as f:
            f.seek(offset)
            line = f.readline()

        record = json.loads(line.decode("utf-8"))
        return record["val"]

    def delete(self, key: str) -> bool:
        """Append a tombstone record and remove the key from the index."""
        if key not in self._index:
            return False

        self._append_record({"op": "del", "key": key})
        del self._index[key]
        return True

    def keys(self) -> list[str]:
        """Return all currently live keys."""
        return list(self._index.keys())


if __name__ == "__main__":
    test_file = Path("test_nexpdb.ndb")
    test_file.unlink(missing_ok=True)

    # 1. Basic set & get
    db = StorageEngine(str(test_file))
    db.set("user:1", {"name": "Alice", "age": 30})
    db.set("user:2", {"name": "Bob", "age": 25})
    assert db.get("user:1") == {"name": "Alice", "age": 30}, "Failed basic get"
    assert db.keys() == ["user:1", "user:2"], "Failed keys check"

    # 2. Update existing key (newest record wins)
    db.set("user:1", {"name": "Alicia", "age": 31})
    assert db.get("user:1") == {"name": "Alicia", "age": 31}, "Failed update"

    # 3. Delete existing and missing keys
    assert db.delete("user:2") is True, "Should return True when deleting existing key"
    assert db.delete("user:2") is False, "Should return False when key already deleted"
    assert db.get("user:2") is None, "Deleted key should return None"
    assert db.keys() == ["user:1"], "Keys should only include live keys"

    # 4. Simulate restart: brand-new instance reads only from disk
    restarted_db = StorageEngine(str(test_file))
    assert restarted_db.get("user:1") == {"name": "Alicia", "age": 31}, "Lost data after restart!"
    assert restarted_db.get("user:2") is None, "Deleted key resurrected after restart!"

    test_file.unlink(missing_ok=True)
    print("ALL STORAGE TESTS PASSED!")

