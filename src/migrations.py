"""
Migrations framework for SQLite local database.
- Tracks applied migrations in table 'migraciones_local'.
- Each migration has a unique string ID and an apply() function.
- Safe to run multiple times: unapplied migrations only.
"""
from __future__ import annotations
from typing import Callable, List, Dict
import datetime

Migration = Dict[str, object]


def _migration_create_indexes(cursor) -> None:
    # Add a couple of helpful indexes (idempotent)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_registros_fecha ON registros_local(fecha)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_registros_empleado_fecha ON registros_local(empleado_id, fecha)")


def _migration_add_double_schedule_columns(conn_or_cursor) -> None:
    """Add columns for double weekly schedule rotation to empleados_local (idempotent).
    Acepta conexión o cursor.
    """
    try:
        c = conn_or_cursor.cursor()
    except AttributeError:
        c = conn_or_cursor
    # Discover existing columns
    c.execute("PRAGMA table_info(empleados_local)")
    cols = {row[1] for row in c.fetchall()}
    def add_col(name: str, ddl: str):
        if name not in cols:
            c.execute(f"ALTER TABLE empleados_local ADD COLUMN {ddl}")
    add_col('hora_entrada_alt', "hora_entrada_alt TEXT")
    add_col('hora_salida_alt', "hora_salida_alt TEXT")
    add_col('rotacion_semanal', "rotacion_semanal INTEGER NOT NULL DEFAULT 0")
    add_col('rotacion_semana_base', "rotacion_semana_base INTEGER NOT NULL DEFAULT 0")


def _migration_normalize_nfc_uids(conn_or_cursor) -> None:
    """Normalize existing NFC UIDs to uppercase without spaces (idempotent)."""
    try:
        c = conn_or_cursor.cursor()
    except AttributeError:
        c = conn_or_cursor
    c.execute("""
        UPDATE empleados_local 
        SET nfc_uid = UPPER(REPLACE(nfc_uid,' ',''))
        WHERE nfc_uid IS NOT NULL
    """)

def _migration_add_daily_exit_overrides(conn_or_cursor) -> None:
    """Add L-V per-day exit columns and enabled flag (idempotent)."""
    try:
        c = conn_or_cursor.cursor()
    except AttributeError:
        c = conn_or_cursor
    c.execute("PRAGMA table_info(empleados_local)")
    cols = {row[1] for row in c.fetchall()}
    def add_if_missing(name: str, ddl: str):
        if name not in cols:
            c.execute(f"ALTER TABLE empleados_local ADD COLUMN {ddl}")
            cols.add(name)
    add_if_missing('salida_por_dia_enabled', 'salida_por_dia_enabled INTEGER NOT NULL DEFAULT 0')
    add_if_missing('salida_lunes', 'salida_lunes TEXT')
    add_if_missing('salida_martes', 'salida_martes TEXT')
    add_if_missing('salida_miercoles', 'salida_miercoles TEXT')
    add_if_missing('salida_jueves', 'salida_jueves TEXT')
    add_if_missing('salida_viernes', 'salida_viernes TEXT')

def _migration_add_daily_entry_overrides(conn_or_cursor) -> None:
    """Add L-V per-day entry columns and a unified enabled flag (idempotent)."""
    try:
        c = conn_or_cursor.cursor()
    except AttributeError:
        c = conn_or_cursor
    c.execute("PRAGMA table_info(empleados_local)")
    cols = {row[1] for row in c.fetchall()}
    def add_if_missing(name: str, ddl: str):
        if name not in cols:
            c.execute(f"ALTER TABLE empleados_local ADD COLUMN {ddl}")
            cols.add(name)
    # Nuevo flag unificado para personalizados (sin romper el existente de salidas)
    add_if_missing('personalizado_por_dia_enabled', 'personalizado_por_dia_enabled INTEGER NOT NULL DEFAULT 0')
    add_if_missing('entrada_lunes', 'entrada_lunes TEXT')
    add_if_missing('entrada_martes', 'entrada_martes TEXT')
    add_if_missing('entrada_miercoles', 'entrada_miercoles TEXT')
    add_if_missing('entrada_jueves', 'entrada_jueves TEXT')
    add_if_missing('entrada_viernes', 'entrada_viernes TEXT')


def get_migrations() -> List[Migration]:
    return [
        {
            "id": "2025-10-13_create_basic_indexes",
            "description": "Create useful indexes on registros_local",
            "apply": _migration_create_indexes,
        },
        {
            "id": "2025-10-13_add_double_schedule_columns",
            "description": "Add columns for weekly rotating double schedule",
            "apply": _migration_add_double_schedule_columns,
        },
        {
            "id": "2025-10-13_normalize_nfc_uids",
            "description": "Normalize NFC UIDs to uppercase without spaces",
            "apply": _migration_normalize_nfc_uids,
        },
        {
            "id": "2025-10-13_add_daily_exit_overrides",
            "description": "Add per-day (Mon-Fri) exit overrides and enabled flag",
            "apply": _migration_add_daily_exit_overrides,
        },
        {
            "id": "2025-10-13_add_daily_entry_overrides",
            "description": "Add per-day (Mon-Fri) entry overrides and unified enabled flag",
            "apply": _migration_add_daily_entry_overrides,
        },
    ]


def ensure_migrations_table(conn) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS migraciones_local (
            id TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL
        )
        """
    )
    conn.commit()


def _already_applied(conn, mig_id: str) -> bool:
    c = conn.cursor()
    c.execute("SELECT 1 FROM migraciones_local WHERE id = ?", (mig_id,))
    return c.fetchone() is not None


def apply_pending_migrations(conn) -> list[str]:
    """Apply pending migrations and return a list of applied IDs."""
    ensure_migrations_table(conn)
    applied: list[str] = []
    for m in get_migrations():
        mig_id = str(m["id"])  # type: ignore
        if _already_applied(conn, mig_id):
            continue
        # Apply migration
        fn: Callable = m["apply"]  # type: ignore
        # Some migrations need full conn (to use PRAGMA/conditional adds)
        cursor = conn.cursor()
        try:
            # Intentar con cursor
            fn(cursor)
        except TypeError:
            # Firma distinta: intentar con conexión
            fn(conn)
        except AttributeError:
            # La función esperaba conexión y recibió cursor
            fn(conn)
        conn.commit()
        # Record applied
        cursor.execute(
            "INSERT INTO migraciones_local (id, applied_at) VALUES (?, ?)",
            (mig_id, datetime.datetime.now().isoformat()),
        )
        conn.commit()
        applied.append(mig_id)
    return applied
