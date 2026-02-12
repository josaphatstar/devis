import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).with_name("inventory.db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            quantity TEXT NOT NULL
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            type TEXT NOT NULL CHECK (type IN ('IN', 'OUT')),
            quantity REAL NOT NULL CHECK (quantity > 0),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
        """
    )

    conn.commit()


def add_product(conn: sqlite3.Connection, name: str, quantity: str) -> None:
    conn.execute(
        "INSERT INTO products(name, quantity) VALUES (?, ?)",
        (name.strip(), quantity.strip()),
    )
    conn.commit()


def list_products(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    cur = conn.execute(
        "SELECT id, name, quantity FROM products ORDER BY name COLLATE NOCASE"
    )
    return list(cur.fetchall())


def add_movement(conn: sqlite3.Connection, product_id: int, mvt_type: str, quantity: float) -> None:
    conn.execute(
        "INSERT INTO movements(product_id, type, quantity) VALUES (?, ?, ?)",
        (product_id, mvt_type, float(quantity)),
    )
    conn.commit()


def list_movements(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    cur = conn.execute(
        """
        SELECT
            m.id,
            m.created_at,
            p.name AS product,
            p.quantity,
            m.type,
            m.quantity
        FROM movements m
        JOIN products p ON p.id = m.product_id
        ORDER BY m.id DESC
        """
    )
    return list(cur.fetchall())


def get_inventory(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    cur = conn.execute(
        """
        SELECT
            p.id,
            p.name,
            p.quantity,
            COALESCE(SUM(CASE WHEN m.type = 'OUT' THEN m.quantity ELSE 0 END), 0) AS total_out,
            CAST(p.quantity AS REAL) - COALESCE(SUM(CASE WHEN m.type = 'OUT' THEN m.quantity ELSE 0 END), 0) AS remaining
        FROM products p
        LEFT JOIN movements m ON m.product_id = p.id
        GROUP BY p.id, p.name, p.quantity
        ORDER BY p.name COLLATE NOCASE
        """
    )
    return list(cur.fetchall())


def get_remaining_for_product(conn: sqlite3.Connection, product_id: int) -> float:
    cur = conn.execute(
        """
        SELECT
            COALESCE(SUM(CASE WHEN type = 'IN' THEN quantity ELSE 0 END), 0)
            - COALESCE(SUM(CASE WHEN type = 'OUT' THEN quantity ELSE 0 END), 0) AS remaining
        FROM movements
        WHERE product_id = ?
        """,
        (product_id,),
    )
    row = cur.fetchone()
    return float(row["remaining"] if row else 0)
