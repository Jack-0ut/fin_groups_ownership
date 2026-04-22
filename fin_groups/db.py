import sqlite3
import pandas as pd
from typing import Iterable, Any

class OwnershipDB:
    def __init__(self, path: str = "ownership.db"):
        self.path = path
        self._init_db()

    # ---------- internal ----------

    def _connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:

            # --- 🔐 Hardening settings ---
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA foreign_keys = ON;")

            # --- Schema ---
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS entities (
                entity_id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                name TEXT NOT NULL,
                country TEXT,
                tax_id TEXT,
                source_url TEXT,
                address TEXT,
                founding_date TEXT,
                status TEXT
            );

            CREATE TABLE IF NOT EXISTS ownerships (
                owner_id TEXT NOT NULL,
                owned_id TEXT NOT NULL,
                role TEXT,
                share_percent REAL,
                capital_uah INTEGER,
                control_level TEXT,
                source TEXT,
                source_url TEXT,
                PRIMARY KEY (owner_id, owned_id),
                FOREIGN KEY(owner_id) REFERENCES entities(entity_id),
                FOREIGN KEY(owned_id) REFERENCES entities(entity_id)
            );

            CREATE INDEX IF NOT EXISTS idx_owner ON ownerships(owner_id);
            CREATE INDEX IF NOT EXISTS idx_owned ON ownerships(owned_id);
            """)
            self._ensure_column(conn, "entities", "address", "address TEXT")
            self._ensure_column(conn, "entities", "founding_date", "founding_date TEXT")
            self._ensure_column(conn, "entities", "status", "status TEXT")

    def _ensure_column(self, conn, table: str, column_name: str, column_def: str):
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        if not any(row[1] == column_name for row in rows):
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column_def}")

    def upsert_entity(self, entity: dict):
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO entities (
                    entity_id, entity_type, name, country, tax_id, source_url,
                    address, founding_date, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(entity_id) DO UPDATE SET
                    name=excluded.name,
                    source_url=excluded.source_url,
                    address=excluded.address,
                    founding_date=excluded.founding_date,
                    status=excluded.status
            """, (
                entity["entity_id"],
                entity["entity_type"],
                entity["name"],
                entity.get("country"),
                entity.get("tax_id"),
                entity.get("source_url"),
                entity.get("address"),
                entity.get("founding_date"),
                entity.get("status"),
            ))

    def upsert_ownership(self, rel: dict):
        with self._connect() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO ownerships (
                    owner_id, owned_id, role,
                    share_percent, capital_uah,
                    control_level, source, source_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rel["owner_id"],
                rel["owned_id"],
                rel.get("role"),
                rel.get("share_percent"),
                rel.get("capital_uah"),
                rel.get("control_level"),
                rel.get("source"),
                rel.get("source_url"),
            ))

    # ---------- reads ----------

    def get_owners_by_tax_id(self, tax_id: str) -> pd.DataFrame:
        sql = """
        SELECT 
            e_owned.tax_id            AS company_tax_id,
            e_owned.name              AS company_name,
            e_owner.entity_id         AS owner_id,
            e_owner.name              AS owner_name,
            e_owner.entity_type       AS owner_type,
            o.share_percent,
            o.capital_uah,
            o.control_level
        FROM entities e_owned
        JOIN ownerships o 
            ON o.owned_id = e_owned.entity_id
        JOIN entities e_owner 
            ON e_owner.entity_id = o.owner_id
        WHERE e_owned.tax_id = ?
        ORDER BY o.share_percent DESC
        """
        return self.query_df(sql, (tax_id,))

    def get_entity(self, entity_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM entities WHERE entity_id = ?",
                (entity_id,)
            ).fetchone()
            return dict(row) if row else None

    def query_df(self, sql: str, params: Iterable[Any] = ()) -> pd.DataFrame:
        with self._connect() as conn:
            return pd.read_sql_query(sql, conn, params=params)

    def query_rows(self, sql: str, params: Iterable[Any] = ()) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]
        
    def get_entity_by_tax_id(self, tax_id: str) -> pd.DataFrame:
        sql = """
            SELECT *
            FROM entities
            WHERE tax_id = ?
        """
        return self.query_df(sql, (tax_id,))


    def extract_group_ids(self, start_id: str) -> set[str]:
        visited = set()
        stack = [start_id]

        with self._connect() as conn:
            while stack:
                cur = stack.pop()
                if cur in visited:
                    continue
                visited.add(cur)

                rows = conn.execute("""
                    SELECT owner_id AS id FROM ownerships WHERE owned_id = ?
                    UNION
                    SELECT owned_id AS id FROM ownerships WHERE owner_id = ?
                """, (cur, cur)).fetchall()

                for r in rows:
                    if r["id"] not in visited:
                        stack.append(r["id"])

        return visited

    def get_group_df(self, start_id: str) -> pd.DataFrame:
        ids = self.extract_group_ids(start_id)
        placeholders = ",".join("?" * len(ids))

        with self._connect() as conn:
            return pd.read_sql_query(
                f"SELECT * FROM entities WHERE entity_id IN ({placeholders})",
                conn,
                params=tuple(ids)
            )

    def get_entity_type(self, entity_id: str) -> str | None:
        ent = self.get_entity(entity_id)
        return ent["entity_type"] if ent else None
