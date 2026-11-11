# NexpDB

A lightweight, append-only database built from scratch in Python. Think of it as a mini Redis meets SQLite, but simpler and educational.

## What is this?

NexpDB is a key-value database that stores data in an append-only log file. It's designed to be easy to understand while demonstrating real database concepts like write-ahead logging, crash recovery, and in-memory indexing.

## Key Features

- **Append-only storage**: All writes go to the end of a log file, making it crash-safe and easy to reason about
- **In-memory indexing**: Fast O(1) lookups using byte offsets instead of scanning the entire file
- **Crash recovery**: Automatically rebuilds the index from disk when restarting
- **Table support**: Named tables with typed schemas (work in progress)
- **Pure Python**: No external dependencies, just the standard library

## How it works

NexpDB uses a simple but clever architecture:

1. **Write path**: Every operation (set, delete) appends a JSON line to the log file
2. **Index**: An in-memory dictionary maps keys to their byte offset in the file
3. **Read path**: Look up the offset, seek to that position, and read the value
4. **Recovery**: On startup, replay the entire log to rebuild the index

The newest record for any key always wins, so updates just append new records rather than modifying the file.

## Usage

### Basic key-value operations

```python
from storage import StorageEngine

# Create or open a database
db = StorageEngine("my_data.ndb")

# Store data
db.set("user:1", {"name": "Alice", "age": 30})
db.set("config:theme", "dark")

# Retrieve data
user = db.get("user:1")  # {"name": "Alice", "age": 30}

# Update (just appends a new record)
db.set("user:1", {"name": "Alice", "age": 31})

# Delete
db.delete("user:1")

# List all keys
all_keys = db.keys()
```

### Working with tables (in development)

```python
from storage import StorageEngine
from tables import TableManager

db = StorageEngine("my_data.ndb")
tables = TableManager(db)

# Create a typed table
tables.create_table("users", {
    "id": "INT",
    "name": "TEXT"
})

# Insert rows
tables.insert("users", {"id": 1, "name": "Alice"})
```

## Running the tests

The storage engine includes built-in tests:

```bash
python storage.py
```

You should see: `ALL STORAGE TESTS PASSED!`

## Project Status

**What works:**
- ✅ Append-only storage engine
- ✅ In-memory indexing
- ✅ Crash recovery
- ✅ Basic CRUD operations

**In progress:**
- 🚧 Table manager with schemas
- 🚧 Type validation
- 🚧 Query support

## Why build this?

This project is a learning exercise in database internals. By implementing storage from scratch, you learn:

- How databases achieve durability
- Why append-only logs are simpler than in-place updates
- How indexing makes lookups fast
- What happens during crash recovery

## Technical Details

### File Format

Each line in the `.ndb` file is a JSON record:

```json
{"op": "set", "key": "user:1", "val": {"name": "Alice", "age": 30}}
{"op": "del", "key": "user:2"}
```

### Performance Characteristics

- **Writes**: O(1) - append to end of file
- **Reads**: O(1) - direct byte offset seek
- **Deletes**: O(1) - append tombstone record
- **Startup**: O(n) - must replay entire log
- **Space**: Grows indefinitely (no compaction yet)

### Limitations

This is an educational project, not production-ready:

- No concurrency control (single-threaded only)
- No compaction (deleted records stay in the file)
- No transactions
- Limited query capabilities
- No network protocol

## License

MIT - feel free to learn from, modify, and share this code.

## Contributing

This is a learning project, but suggestions and improvements are welcome! Open an issue or submit a PR.

---

Built to understand how databases work under the hood 🔍
