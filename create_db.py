"""Reconstruye data/curso.sqlite a partir de los CSV incluidos."""

import sqlite3
from pathlib import Path

import pandas as pd


data_dir = Path(__file__).resolve().parent / "data"
database = data_dir / "curso.sqlite"
if database.exists():
    database.unlink()

with sqlite3.connect(database) as connection:
    for table in ("ventas", "clientes", "pedidos", "estudiantes"):
        pd.read_csv(data_dir / f"{table}.csv").to_sql(table, connection, index=False)

print(f"Base creada: {database}")
