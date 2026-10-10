"""Ejecución de prácticas en el navegador para la edición pública de DataLab.

El código del visitante nunca se envía a un intérprete del servidor.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

import streamlit as st


ROOT = Path(__file__).resolve().parent
TEMPLATE = (ROOT / "web_lab.html").read_text(encoding="utf-8")


def show_browser_result(route: str, code: str, solution: str = "", check: str = "") -> None:
    language = {"Python": "python", "SQL": "sql", "R": "r"}[route]
    config: dict = {"language": language, "code": code, "solution": solution, "check": check}
    if language == "sql":
        config["database"] = base64.b64encode((ROOT / "data" / "curso.sqlite").read_bytes()).decode("ascii")
    else:
        config["csv"] = {
            path.name: path.read_text(encoding="utf-8-sig")
            for path in (ROOT / "data").glob("*.csv")
        }
    # '<' escapado evita que un texto del editor cierre el elemento <script>.
    payload = json.dumps(config, ensure_ascii=True).replace("<", "\\u003c")
    st.iframe(TEMPLATE.replace("/*__CONFIG__*/ null", payload), height=650)
