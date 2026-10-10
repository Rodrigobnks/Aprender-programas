"""Ejecución local de prácticas Python, SQL, R y verificación guiada de DAX."""

from __future__ import annotations

import base64
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"


def run_python(code: str) -> dict:
    if os.environ.get("DATALAB_PUBLIC_MODE") == "1":
        return {"stdout": "", "error": "La ejecución pública de Python ocurre solo en el navegador.", "images": []}
    if not code.strip():
        return {"stdout": "", "error": "Escribe código antes de ejecutarlo.", "images": []}
    if len(code) > 12000:
        return {"stdout": "", "error": "El código supera 12 000 caracteres.", "images": []}
    try:
        process = subprocess.run(
            [sys.executable, "-I", str(ROOT / "python_worker.py")],
            input=code,
            capture_output=True,
            text=True,
            cwd=ROOT,
            timeout=30,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"stdout": "", "error": "La ejecución superó 30 segundos. Revisa si hay un bucle largo.", "images": []}
    try:
        result = json.loads(process.stdout)
    except json.JSONDecodeError:
        return {"stdout": "", "error": (process.stderr or process.stdout or "No se obtuvo un resultado.")[:12000], "images": []}
    return {
        "stdout": result.get("stdout", ""),
        "error": result.get("error", ""),
        "images": [base64.b64decode(item) for item in result.get("images", [])[:3]],
    }


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    for name in ("ventas", "clientes", "pedidos", "estudiantes"):
        pd.read_csv(DATA / f"{name}.csv").to_sql(name, connection, index=False)
    return connection


def _statements(code: str) -> list[str]:
    statements: list[str] = []
    buffer = ""
    for line in code.splitlines(keepends=True):
        buffer += line
        if sqlite3.complete_statement(buffer):
            statements.append(buffer.strip())
            buffer = ""
    if buffer.strip():
        statements.append(buffer.strip())
    return statements


def run_sql(code: str) -> dict:
    if os.environ.get("DATALAB_PUBLIC_MODE") == "1":
        return {"table": None, "message": "", "error": "La ejecución pública de SQL ocurre solo en el navegador."}
    if not code.strip():
        return {"table": None, "message": "", "error": "Escribe una consulta antes de ejecutarla."}
    if len(code) > 12000:
        return {"table": None, "message": "", "error": "La consulta supera 12 000 caracteres."}
    statements = _statements(code)
    if len(statements) > 20:
        return {"table": None, "message": "", "error": "Usa como máximo 20 instrucciones por ejecución."}
    connection = _connection()
    ticks = 0

    def limit() -> int:
        nonlocal ticks
        ticks += 1
        return int(ticks > 300)

    def authorize(action, _arg1, _arg2, _database, _source):
        blocked = {
            sqlite3.SQLITE_ATTACH,
            sqlite3.SQLITE_DETACH,
            sqlite3.SQLITE_PRAGMA,
        }
        return sqlite3.SQLITE_DENY if action in blocked else sqlite3.SQLITE_OK

    connection.set_progress_handler(limit, 1000)
    connection.set_authorizer(authorize)
    try:
        table = None
        message = ""
        for statement in statements:
            cursor = connection.execute(statement)
            if cursor.description:
                rows = cursor.fetchmany(501)
                if len(rows) > 500:
                    raise ValueError("La consulta devolvió más de 500 filas; usa LIMIT.")
                table = pd.DataFrame(rows, columns=[item[0] for item in cursor.description])
                message = f"Consulta ejecutada: {len(table)} filas."
            else:
                message = f"Instrucción ejecutada: {cursor.rowcount} filas afectadas."
        return {"table": table, "message": message, "error": ""}
    except Exception as exc:
        return {"table": None, "message": "", "error": f"{type(exc).__name__}: {exc}"}
    finally:
        connection.close()


def find_rscript() -> str | None:
    found = shutil.which("Rscript")
    if found:
        return found
    candidates = sorted(Path("C:/Program Files/R").glob("R-*/bin/Rscript.exe"))
    return str(candidates[-1]) if candidates else None


def run_r(code: str) -> dict:
    if os.environ.get("DATALAB_PUBLIC_MODE") == "1":
        return {"stdout": "", "error": "La ejecución pública de R ocurre solo en el navegador.", "images": []}
    rscript = find_rscript()
    if not rscript:
        return {"stdout": "", "error": "Rscript no está instalado. Instala R para ejecutar estas prácticas; mientras tanto puedes escribir y comparar tu solución.", "images": []}
    if not code.strip():
        return {"stdout": "", "error": "Escribe código antes de ejecutarlo.", "images": []}
    if len(code) > 12000:
        return {"stdout": "", "error": "El código supera 12 000 caracteres.", "images": []}
    with tempfile.TemporaryDirectory(prefix="datalab_r_") as temporary:
        plot_path = Path(temporary) / "grafica.png"
        r_wrapper = (
            "codigo <- paste(readLines('stdin', warn=FALSE), collapse='\\n'); "
            "png(commandArgs(trailingOnly=TRUE)[1]); "
            "tryCatch({ expresiones <- parse(text=codigo); "
            "for (expresion in expresiones) { valor <- withVisible(eval(expresion, .GlobalEnv)); "
            "if (valor$visible && inherits(valor$value, 'ggplot')) print(valor$value) } }, "
            "error=function(e) { message(conditionMessage(e)); quit(status=1) }); "
            "dev.off()"
        )
        try:
            process = subprocess.run(
                [rscript, "--vanilla", "-e", r_wrapper, str(plot_path)],
                input=code,
                capture_output=True,
                text=True,
                cwd=ROOT,
                timeout=15,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {"stdout": "", "error": "R superó 15 segundos; revisa el código.", "images": []}
        images = []
        if plot_path.exists() and plot_path.stat().st_size > 1500:
            images.append(plot_path.read_bytes())
        return {
            "stdout": (process.stdout or "")[:20000],
            "error": (process.stderr or "")[:12000] if process.returncode else "",
            "images": images,
        }


def normalize_dax(formula: str) -> str:
    expression = formula.split("=", 1)[-1] if "=" in formula else formula
    expression = expression.replace(";", ",")
    return re.sub(r"\s+", "", expression).casefold()


def check_dax(formula: str, solution: str) -> tuple[bool, str]:
    if not formula.strip():
        return False, "Escribe una fórmula DAX antes de comprobarla."
    if normalize_dax(formula) == normalize_dax(solution):
        return True, "La fórmula coincide con la solución propuesta. Pruébala en Power BI Desktop para ver su resultado en el modelo."
    return False, "La fórmula aún no coincide con la solución propuesta. Revisa funciones, columnas y filtros; después compárala con la pista."
