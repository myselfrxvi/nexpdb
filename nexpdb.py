import sys 
from typing import Any

from parser import CreateTableStmt, DeleteStmt, InsertStmt, SelectStmt, parse_sql

from storage import StorageEngine
from tables import TableManager

def format_table(rows: list[dict[str, any]]) -> str:
    if not rows:
        return "Empty  set."

    columns = list(rows[0].keys())

    widths = {
        col: max(len(col), max(len(str(row.get(col, ""))) for row in rows))
        for col in columns
    }

    divider = "+" + "+".join("-" * (widths[c] + 2) for c in columns) + "+"
    header = "| " + " | ".join(f"{c:<{widths[c]}}" for c in columns) + " |"

    lines = [divider, header, divider]
    for row in rows:
        row_str = "| " + " | ".join(f"{str(row.get(c, '')):<{widths[c]}}" for c in columns) + " |"
        lines.append(row_str)
    lines.append(divider)
    lines.append(f"{len(rows)} row(s) in set.")
    return "\n".join(lines)

class NexpDB:
    def __init__(self, filepath: str = "nexpdb.ndb") -> None:
        self.storage = StorageEngine(filepath)
        self.tables = TableManager(self.storage)

    def execute(self, sql: str) -> str | list[dict[str, Any]]:
        stmt = parse_sql(sql)
        
        if isinstance(stmt, CreateTableStmt):
            self.tables.create_table(stmt.table, stmt.columns)
            return f"Table '{stmt.table}' created."

        if isinstance(stmt, InsertStmt):
            schema: schema = self.tables._get_schema(stmt.table)
            if len(stmt.values) != len(schema):
                raise ValueError("Number of values does not match number of columns.")
            row: row = dict(zip(schema.keys(), stmt.values))
            self.tables.insert(stmt.table, row)
            return f"1 row inserted."

        if isinstance(stmt, SelectStmt):
            rows = self.tables.select(stmt.table, where=stmt.where)
            if stmt.columns is not None:
                rows = [{col: r[col] for col in stmt.columns if col in r} for r in rows]
            return rows

        if isinstance(stmt, DeleteStmt):
            col, val = stmt.where
            count = self.tables.delete_where(stmt.table, col, val)   
            return f"{count} row(s) deleted"

        raise ValueError("Implement statement execution branches")
        
def repl(db_file: str = "nexpdb.ndb") -> None:
    db = NexpDB(db_file)
    print(f"Connected to NexpDB ({db_file}). Type SQL or .exit to quit.")
    while True:
        try:
            line = input("nexpdb> ").strip()
            if not line:
                continue
            if line in (".exit", ".quit", "exit", "quit"):
                print("Bye!")
                break
            if line == ".tables":
                tables = [k.split(":", 1)[1] for k in db.storage.keys() if k.startswith("__schema__:")]
                print("Tables:", ", ".join(tables) if tables else "None")
                continue
            result = db.execute(line)
            if isinstance(result, list):
                print(format_table(result))
            else:
                print(result)
        except (ValueError, EOFError, KeyboardInterrupt) as e:
            if isinstance(e, (EOFError, KeyboardInterrupt)):
                print("\nBye!")
                break
            print(f"Error: {e}")
if __name__ == "__main__":
    db_name = sys.argv[1] if len(sys.argv) > 1 else "nexpdb.ndb"
    repl(db_name)
