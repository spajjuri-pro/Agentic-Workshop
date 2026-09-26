"""Load seed/tickets.csv and seed/customers.csv into a local SQLite app.db.

Usage: uv run python load_seed.py
"""

import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "app.db"
TICKETS_CSV = ROOT / "seed" / "tickets.csv"
CUSTOMERS_CSV = ROOT / "seed" / "customers.csv"


def _read_csv(path: Path) -> tuple[list[str], list[tuple]]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = [tuple(row) for row in reader]
    return header, rows


def load_seed(db_path: Path = DB_PATH) -> None:
    """Create app.db with tickets and customers tables from the seed CSVs.

    Idempotent: dropping and recreating the tables each run yields the same
    database, so running twice produces identical contents.
    """
    tickets_header, tickets_rows = _read_csv(TICKETS_CSV)
    customers_header, customers_rows = _read_csv(CUSTOMERS_CSV)
    customers_rows = [
        tuple(
            int(value) if column == "open_tickets" else value
            for column, value in zip(customers_header, row)
        )
        for row in customers_rows
    ]

    with sqlite3.connect(db_path) as conn:
        conn.execute("DROP TABLE IF EXISTS tickets")
        conn.execute("DROP TABLE IF EXISTS customers")

        tickets_cols = ", ".join(tickets_header)
        customers_cols = ", ".join(
            f"{column} INTEGER" if column == "open_tickets" else column
            for column in customers_header
        )
        customers_insert_cols = ", ".join(customers_header)
        conn.execute(f"CREATE TABLE tickets ({tickets_cols})")
        conn.execute(f"CREATE TABLE customers ({customers_cols})")

        conn.executemany(
            f"INSERT INTO tickets ({tickets_cols}) VALUES ({', '.join('?' * len(tickets_header))})",
            tickets_rows,
        )
        conn.executemany(
            f"INSERT INTO customers ({customers_insert_cols}) VALUES ({', '.join('?' * len(customers_header))})",
            customers_rows,
        )


if __name__ == "__main__":
    load_seed()
    print(f"Loaded {TICKETS_CSV.name} and {CUSTOMERS_CSV.name} into {DB_PATH.name}")