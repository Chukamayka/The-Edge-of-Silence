import sqlite3
from datetime import datetime
from pathlib import Path
from core.paths import database_path


class RunDatabase:
    def __init__(self, db_path=None):
        self.db_path = Path(db_path) if db_path else database_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    level INTEGER NOT NULL,
                    difficulty INTEGER NOT NULL,
                    time_seconds REAL NOT NULL,
                    deaths INTEGER NOT NULL,
                    stones_thrown INTEGER NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS records (
                    level INTEGER NOT NULL,
                    difficulty INTEGER NOT NULL,
                    best_time_seconds REAL NOT NULL,
                    deaths INTEGER NOT NULL,
                    stones_thrown INTEGER NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY(level, difficulty)
                )
                """
            )

    def save_run(self, level, difficulty, timer):
        now = datetime.utcnow().isoformat(timespec="seconds")
        is_new_record = False
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO runs (created_at, level, difficulty, time_seconds, deaths, stones_thrown)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (now, int(level), int(difficulty), float(timer.time), int(timer.deaths), int(timer.stones_thrown)),
            )

            row = conn.execute(
                """
                SELECT best_time_seconds
                FROM records
                WHERE level = ? AND difficulty = ?
                """,
                (int(level), int(difficulty)),
            ).fetchone()

            if row is None or float(timer.time) < float(row[0]):
                is_new_record = True
                conn.execute(
                    """
                    INSERT INTO records (level, difficulty, best_time_seconds, deaths, stones_thrown, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(level, difficulty) DO UPDATE SET
                        best_time_seconds=excluded.best_time_seconds,
                        deaths=excluded.deaths,
                        stones_thrown=excluded.stones_thrown,
                        updated_at=excluded.updated_at
                    """,
                    (
                        int(level),
                        int(difficulty),
                        float(timer.time),
                        int(timer.deaths),
                        int(timer.stones_thrown),
                        now,
                    ),
                )
        return is_new_record

    def get_best_record(self, level, difficulty):
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT best_time_seconds, deaths, stones_thrown, updated_at
                FROM records
                WHERE level = ? AND difficulty = ?
                """,
                (int(level), int(difficulty)),
            ).fetchone()
        if row is None:
            return None
        return {
            "best_time_seconds": float(row[0]),
            "deaths": int(row[1]),
            "stones_thrown": int(row[2]),
            "updated_at": row[3],
        }

    def get_top_runs(self, limit=10):
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT created_at, level, difficulty, time_seconds, deaths, stones_thrown
                FROM runs
                ORDER BY time_seconds ASC
                LIMIT ?
                """,
                (int(limit),),
            ).fetchall()
        return [
            {
                "created_at": row[0],
                "level": int(row[1]),
                "difficulty": int(row[2]),
                "time_seconds": float(row[3]),
                "deaths": int(row[4]),
                "stones_thrown": int(row[5]),
            }
            for row in rows
        ]

    def get_records_for_difficulty(self, difficulty):
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT level, best_time_seconds, deaths, stones_thrown
                FROM records
                WHERE difficulty = ?
                ORDER BY level ASC
                """,
                (int(difficulty),),
            ).fetchall()
        return [
            {
                "level": int(row[0]),
                "best_time_seconds": float(row[1]),
                "deaths": int(row[2]),
                "stones_thrown": int(row[3]),
            }
            for row in rows
        ]

    def get_top_runs_by_difficulty(self, difficulty, limit=5):
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT created_at, level, time_seconds, deaths, stones_thrown
                FROM runs
                WHERE difficulty = ?
                ORDER BY time_seconds ASC
                LIMIT ?
                """,
                (int(difficulty), int(limit)),
            ).fetchall()
        return [
            {
                "created_at": row[0],
                "level": int(row[1]),
                "time_seconds": float(row[2]),
                "deaths": int(row[3]),
                "stones_thrown": int(row[4]),
            }
            for row in rows
        ]
