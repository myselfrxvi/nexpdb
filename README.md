# NexpDB 💾

> **"How does a database actually work when you don't use SQLite or external libraries?"**  
> I had no idea, so I built one from scratch in pure Python.

NexpDB is a relational SQL database engine written with zero third-party dependencies. It combines a **Bitcask-style append-only storage engine** on disk with a **hand-written SQL lexer, parser, and interactive REPL**.

---

## ⚡ Quick Demo

Start the database shell:

```powershell
python nexpdb.py
```

Then write real SQL:

```text
Connected to NexpDB (nexpdb.ndb). Type SQL or .exit to quit.

nexpdb> CREATE TABLE users (id INT, name TEXT);
Table 'users' created.

nexpdb> INSERT INTO users VALUES (1, 'Alice');
1 row inserted.

nexpdb> INSERT INTO users VALUES (2, 'Bob');
1 row inserted.

nexpdb> SELECT * FROM users;
+----+-------+
| id | name  |
+----+-------+
| 1  | Alice |
| 2  | Bob   |
+----+-------+
2 row(s) in set.

nexpdb> DELETE FROM users WHERE id = 2;
1 row(s) deleted

nexpdb> SELECT * FROM users;
+----+-------+
| id | name  |
+----+-------+
| 1  | Alice |
+----+-------+
1 row(s) in set.

nexpdb> .tables
Tables: users

nexpdb> .exit
Bye!
```

Shutdown your terminal, reopen it, and run `SELECT * FROM users;` again—your data is still there.

---

## 🧠 How It Works Under The Hood

NexpDB is built in 4 clean, decoupled layers:

```text
  SQL String: "SELECT name FROM users WHERE id = 1;"
                          │
                          ▼
             ┌─────────────────────────┐
             │ 1. Lexer & Parser       │  Chops text into tokens & builds AST
             │    (parser.py)          │  (SelectStmt, InsertStmt, etc.)
             └────────────┬────────────┘
                          ▼
             ┌─────────────────────────┐
             │ 2. Executor & REPL      │  Interactive terminal + routes AST
             │    (nexpdb.py)          │  to the TableManager
             └────────────┬────────────┘
                          ▼
             ┌─────────────────────────┐
             │ 3. Table & Schema Layer │  Enforces typed schemas (INT, TEXT)
             │    (tables.py)          │  and namespaces rows
             └────────────┬────────────┘
                          ▼
             ┌─────────────────────────┐
             │ 4. Storage Engine       │  Append-only binary log + in-memory
             │    (storage.py)         │  byte-offset index
             └────────────┬────────────┘
                          ▼
                    Disk: nexpdb.ndb
```

---

### Layer 1: The Append-Only Log (`storage.py`)
Most beginners assume databases open a file, find line 4, and edit `"Alice"` to `"Alicia"`. **Databases don't do that.**

Editing in the middle of a file means shifting thousands of bytes and risks corrupting everything if power cuts out mid-write. 

Instead, NexpDB treats the file like an accounting ledger in permanent ink:
- **Writes are append-only:** Every `SET` or `DELETE` simply appends one new line to the bottom of `nexpdb.ndb`.
- **In-memory Table of Contents:** Scanning a huge file for every read would be slow. When the engine boots up, it reads the log once and remembers `{key: byte_offset}` in RAM. Looking up any key takes `O(1)`: seek straight to that byte offset and read that single record.
- **Tombstones:** To delete a key without erasing past bytes, we append a `{"op": "del", "key": ...}` tombstone. When replaying the file on restart, hitting a tombstone removes that key from the in-memory index.

### Layer 2: Relational Tables & Schemas (`tables.py`)
How do tables live inside a flat key-value store? **Key prefixes:**
- Blueprints are stored under `"__schema__:<table_name>"` (e.g. `{"id": "INT", "name": "TEXT"}`).
- Rows are saved as `"row:<table_name>:<uuid>"` (e.g. `{"id": 1, "name": "Alice"}`).
- Type checking happens before anything touches disk—trying to insert text into an `INT` column throws an immediate error.

### Layer 3: Hand-Written SQL Parser (`parser.py`)
No `sqlparse` or third-party libraries.
- **Tokenizer:** Walks the string character-by-character to properly separate symbols (`(`, `)`, `,`, `;`, `=`), negative numbers (`-5`), and quoted strings (`'Alice Smith'`).
- **Parser:** Reads tokens sequentially to produce typed `@dataclass` commands:
  - `CreateTableStmt(table, columns)`
  - `InsertStmt(table, values)`
  - `SelectStmt(table, columns, where)`
  - `DeleteStmt(table, where)`

### Layer 4: Executor & Terminal UI (`nexpdb.py`)
- Translates parsed AST statements into table operations.
- Dynamically calculates column widths and renders results into ASCII tables.
- Implements a resilient interactive REPL loop with dot commands (`.tables`, `.exit`).

---

## 🔍 Peek Behind The Curtain: The Disk File

Open `nexpdb.ndb` in Notepad or VS Code right now. You won't see magic or encrypted blobs; you will see the exact raw ledger of actions:

```json
{"op": "set", "key": "__schema__:users", "val": {"id": "INT", "name": "TEXT"}}
{"op": "set", "key": "row:users:27f08211d4d5", "val": {"id": 1, "name": "Alice"}}
{"op": "set", "key": "row:users:d0aca1e6029d", "val": {"id": 2, "name": "Bob"}}
{"op": "del", "key": "row:users:d0aca1e6029d"}
```

Notice line 4? That's the **tombstone** deleting Bob. Bob's older row is still physically on disk, but the database knows he's gone!

---

## 🧪 Running The Verification Suites

Each layer contains its own standalone, non-tautological test suite:

```powershell
# Test the append-only storage engine (offset seeks, restarts, tombstones)
python storage.py

# Test schema creation, type validation, table isolation, row queries
python tables.py

# Test tokenizer and SQL grammar parser
python parser.py
```

All three will output:
```text
ALL STORAGE TESTS PASSED!
ALL TABLE TESTS PASSED!
ALL PARSER TESTS PASSED!
```

---

## 💡 What I Learned Building This

1. **Why databases love append-only logs:** Appends are fast, safe from partial-write corruption, and simple to reason about.
2. **What an "Index" actually is:** It's not magic—it's just a Python dictionary in memory that remembers exact byte offsets so you can `f.seek()` instantly.
3. **Compilers and Parsers aren't scary:** Splitting raw text into `Tokens` first makes parsing SQL grammar surprisingly straightforward.
4. **Mechanical Sympathy:** Real software is about organizing bytes on a hard drive and moving them into memory efficiently.

---

## 🚀 What's Next?
- [ ] **Log Compaction:** A background worker that merges `nexpdb.ndb` to clean out dead rows and tombstones to reclaim disk space.
- [ ] **Secondary Indexes:** Adding a B-Tree or hash map on specific columns so `WHERE name = 'Alice'` doesn't require a full table scan.
- [ ] **JOIN queries:** Joining two tables across foreign keys.

---

*Built manually from scratch in Python.*
