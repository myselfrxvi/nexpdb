from inspect import istraceback
from _winapi import CREATE_BREAKAWAY_FROM_JOB
import sys 
from typing import Any

from parser import CreateTableStmt, DeleteStmt, InsertStmt, SelectStmt, parse_sql

from storage import StorageEngine
from tables import TableManager

def formart_table(rows: list[dict[str, any]]) -> str:
    if not rows:
        return "Empty  set."

    columns = list(rows[0].keys())

    widths = {
        col: max(len(col), max(len(str(rows.get(col, ""))) for row in rows))
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

class nexpdb:
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
            rows: rows = self.tables.select(stmt.table, where=stmt.where)
            if stmt.colums is None:
                filter
                
