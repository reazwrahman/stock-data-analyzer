#!/usr/bin/env python3
"""
Load merged_data.json into a local SQLite database.

This script:
1) Reads rows from merged_data.json (expected: list of objects).
2) Creates a SQLite database if it does not exist.
3) Creates a table with columns matching the JSON structure.
4) Inserts all rows into the table.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

JSON_PATH = Path("merged_data.json")
DB_PATH = Path("merged_data.db")
TABLE_NAME = "merged_positions"
LAST_UPDATED_COLUMN = "last_updated_est"
SOURCE_COLUMN = "source"


def quote_identifier(identifier: str) -> str:
    # Double quotes escape SQLite identifiers safely.
    return '"' + identifier.replace('"', '""') + '"'


def infer_sqlite_type(values: list[Any]) -> str:
    non_null = [value for value in values if value is not None]
    if not non_null:
        return "TEXT"

    if all(isinstance(value, bool) for value in non_null):
        return "INTEGER"

    if all(isinstance(value, int) and not isinstance(value, bool) for value in non_null):
        return "INTEGER"

    if all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in non_null):
        return "REAL"

    return "TEXT"


def load_rows(json_path: Path) -> list[dict[str, Any]]:
    with json_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("Expected merged_data.json to contain a list of objects.")

    rows = [row for row in data if isinstance(row, dict)]
    if not rows:
        raise ValueError("No object rows found in merged_data.json.")
    return rows


def build_schema(rows: list[dict[str, Any]]) -> tuple[list[str], dict[str, str]]:
    columns: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                columns.append(key)

    column_types: dict[str, str] = {}
    for column in columns:
        values = [row.get(column) for row in rows]
        column_types[column] = infer_sqlite_type(values)

    if SOURCE_COLUMN not in columns:
        columns.append(SOURCE_COLUMN)
        column_types[SOURCE_COLUMN] = "TEXT"

    if LAST_UPDATED_COLUMN not in columns:
        columns.append(LAST_UPDATED_COLUMN)
        column_types[LAST_UPDATED_COLUMN] = "TEXT"

    return columns, column_types


def create_table(conn: sqlite3.Connection, columns: list[str], column_types: dict[str, str]) -> None:
    conn.execute(f"DROP TABLE IF EXISTS {quote_identifier(TABLE_NAME)}")
    column_defs = ", ".join(
        f"{quote_identifier(column)} {column_types[column]}" for column in columns
    )
    sql = f"""
    CREATE TABLE {quote_identifier(TABLE_NAME)} (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      {column_defs}
    )
    """
    conn.execute(sql)


def replace_table_data(conn: sqlite3.Connection, rows: list[dict[str, Any]], columns: list[str]) -> None:
    placeholders = ", ".join("?" for _ in columns)
    quoted_columns = ", ".join(quote_identifier(column) for column in columns)
    insert_sql = f"""
    INSERT INTO {quote_identifier(TABLE_NAME)} ({quoted_columns})
    VALUES ({placeholders})
    """

    payload = [tuple(row.get(column) for column in columns) for row in rows]
    conn.executemany(insert_sql, payload)


def main() -> None:
    rows = load_rows(JSON_PATH)
    est_now = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d %I:%M:%S %p %Z")
    rows = [{**row, SOURCE_COLUMN: row.get(SOURCE_COLUMN), LAST_UPDATED_COLUMN: est_now} for row in rows]
    columns, column_types = build_schema(rows)

    with sqlite3.connect(DB_PATH) as conn:
        create_table(conn, columns, column_types)
        replace_table_data(conn, rows, columns)
        conn.commit()

    print(f"Loaded rows: {len(rows)}")
    print(f"Database: {DB_PATH.resolve()}")
    print(f"Table: {TABLE_NAME}")
    print(f"Columns: {columns}")


if __name__ == "__main__":
    main()
