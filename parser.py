from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Token:
    kind: str   # "WORD", "NUMBER", "STRING", "SYMBOL"
    value: Any


@dataclass(frozen=True, slots=True)
class CreateTableStmt:
    table: str
    columns: dict[str, str]


@dataclass(frozen=True, slots=True)
class InsertStmt:
    table: str
    values: list[Any]


@dataclass(frozen=True, slots=True)
class SelectStmt:
    table: str
    columns: list[str] | None  # None means "*" (all columns)
    where: tuple[str, Any] | None


@dataclass(frozen=True, slots=True)
class DeleteStmt:
    table: str
    where: tuple[str, Any]


Statement = CreateTableStmt | InsertStmt | SelectStmt | DeleteStmt


def tokenize(sql: str) -> list[Token]:
    """Convert raw SQL text into a flat list of typed Tokens."""
    tokens: list[Token] = []
    i = 0
    n = len(sql)

    while i < n:
        ch = sql[i]

        if ch.isspace():
            i += 1
        elif ch in "(),;=*":
            tokens.append(Token("SYMBOL", ch))
            i += 1
        elif ch in ("'", '"'):
            quote = ch
            i += 1
            start = i
            while i < n and sql[i] != quote:
                i += 1
            if i >= n:
                raise ValueError("Unterminated string literal")
            tokens.append(Token("STRING", sql[start:i]))
            i += 1  # Skip closing quote
        elif ch.isdigit() or (ch == "-" and i + 1 < n and sql[i + 1].isdigit()):
            start = i
            i += 1
            while i < n and sql[i].isdigit():
                i += 1
            tokens.append(Token("NUMBER", int(sql[start:i])))
        elif ch.isalpha() or ch == "_":
            start = i
            while i < n and (sql[i].isalnum() or sql[i] == "_"):
                i += 1
            tokens.append(Token("WORD", sql[start:i]))
        else:
            raise ValueError(f"Unexpected character in SQL: {ch!r}")

    return tokens


class Parser:
    """Turns a list of Tokens into a structured SQL Statement object."""

    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.pos = 0

    def _peek(self) -> Token | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _advance(self) -> Token:
        tok = self._peek()
        if tok is None:
            raise ValueError("Unexpected end of SQL statement")
        self.pos += 1
        return tok

    def _match_symbol(self, sym: str) -> bool:
        tok = self._peek()
        if tok and tok.kind == "SYMBOL" and tok.value == sym:
            self.pos += 1
            return True
        return False

    def _match_keyword(self, kw: str) -> bool:
        tok = self._peek()
        if tok and tok.kind == "WORD" and tok.value.upper() == kw:
            self.pos += 1
            return True
        return False

    def _expect(self, kind: str, value: str | None = None) -> Token:
        tok = self._advance()
        if tok.kind != kind:
            raise ValueError(f"Expected {kind}, got {tok.kind} ({tok.value!r})")
        if value is not None:
            actual = tok.value.upper() if kind == "WORD" else tok.value
            if actual != value:
                raise ValueError(f"Expected {value!r}, got {tok.value!r}")
        return tok

    def _parse_value(self) -> Any:
        tok = self._advance()
        if tok.kind in ("NUMBER", "STRING"):
            return tok.value
        raise ValueError(f"Expected literal value (number or string), got {tok.value!r}")

    def _parse_where(self) -> tuple[str, Any] | None:
        if not self._match_keyword("WHERE"):
            return None
        col = self._expect("WORD").value
        self._expect("SYMBOL", "=")
        val = self._parse_value()
        return (col, val)

    def parse(self) -> Statement:
        tok = self._peek()
        if tok is None or tok.kind != "WORD":
            raise ValueError("SQL statement must start with a keyword")

        kw = tok.value.upper()
        if kw == "CREATE":
            stmt: Statement = self._parse_create()
        elif kw == "INSERT":
            stmt = self._parse_insert()
        elif kw == "SELECT":
            stmt = self._parse_select()
        elif kw == "DELETE":
            stmt = self._parse_delete()
        else:
            raise ValueError(f"Unsupported SQL command: {tok.value!r}")

        self._match_symbol(";")
        trailing = self._peek()
        if trailing is not None:
            raise ValueError(f"Unexpected trailing token: {trailing.value!r}")
        return stmt

    def _parse_create(self) -> CreateTableStmt:
        self._expect("WORD", "CREATE")
        self._expect("WORD", "TABLE")
        table = self._expect("WORD").value
        self._expect("SYMBOL", "(")

        columns: dict[str, str] = {}
        while True:
            col_name = self._expect("WORD").value
            col_type = self._expect("WORD").value.upper()
            columns[col_name] = col_type
            if not self._match_symbol(","):
                break

        self._expect("SYMBOL", ")")
        return CreateTableStmt(table=table, columns=columns)

    def _parse_insert(self) -> InsertStmt:
        self._expect("WORD", "INSERT")
        self._expect("WORD", "INTO")
        table = self._expect("WORD").value
        self._expect("WORD", "VALUES")
        self._expect("SYMBOL", "(")

        values: list[Any] = []
        while True:
            values.append(self._parse_value())
            if not self._match_symbol(","):
                break

        self._expect("SYMBOL", ")")
        return InsertStmt(table=table, values=values)

    def _parse_select(self) -> SelectStmt:
        self._expect("WORD", "SELECT")
        if self._match_symbol("*"):
            columns = None
        else:
            columns = []
            while True:
                columns.append(self._expect("WORD").value)
                if not self._match_symbol(","):
                    break

        self._expect("WORD", "FROM")
        table = self._expect("WORD").value
        where = self._parse_where()
        return SelectStmt(table=table, columns=columns, where=where)

    def _parse_delete(self) -> DeleteStmt:
        self._expect("WORD", "DELETE")
        self._expect("WORD", "FROM")
        table = self._expect("WORD").value
        where = self._parse_where()
        if where is None:
            raise ValueError("DELETE requires a WHERE clause")
        return DeleteStmt(table=table, where=where)


def parse_sql(sql: str) -> Statement:
    """Convenience entry point: tokenize + parse one SQL statement."""
    return Parser(tokenize(sql)).parse()


# --- Verification Harness (Do not modify) ---
if __name__ == "__main__":
    # 1. CREATE TABLE
    assert parse_sql("CREATE TABLE users (id INT, name TEXT);") == CreateTableStmt(
        table="users", columns={"id": "INT", "name": "TEXT"}
    )

    # 2. INSERT with space inside string & negative int
    assert parse_sql("INSERT INTO users VALUES (-1, 'Alice Smith');") == InsertStmt(
        table="users", values=[-1, "Alice Smith"]
    )

    # 3. SELECT * (case-insensitive keywords)
    assert parse_sql("select * from users;") == SelectStmt(
        table="users", columns=None, where=None
    )

    # 4. SELECT specific columns with WHERE
    assert parse_sql("Select name, id From users Where id = 2;") == SelectStmt(
        table="users", columns=["name", "id"], where=("id", 2)
    )

    # 5. DELETE with WHERE
    assert parse_sql("DELETE FROM users WHERE name = 'Alice Smith';") == DeleteStmt(
        table="users", where=("name", "Alice Smith")
    )

    # 6. Bad syntax raises ValueError
    for bad in ["", "DROP TABLE users;", "SELECT * users;", "INSERT INTO users VALUES ('unclosed);"]:
        try:
            parse_sql(bad)
            assert False, f"Should have rejected: {bad}"
        except ValueError:
            pass

    print("ALL PARSER TESTS PASSED!")