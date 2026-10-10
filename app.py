"""DataLab: curso interactivo de Python, SQL, R y Power BI/DAX."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pandas as pd
import streamlit as st

from curriculum import CURRICULUM, LEVELS, REVIEW
from runtime import DATA, ROOT, check_dax, find_rscript, run_python, run_r, run_sql


PROGRESS_FILE = ROOT / "progreso.json"
PUBLIC_MODE = os.environ.get("DATALAB_PUBLIC_MODE") == "1"

if PUBLIC_MODE:
    from browser_lab import show_browser_result


def load_progress() -> dict:
    if PUBLIC_MODE:
        return {"completed": set(), "review": None}
    try:
        raw = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
        return {"completed": set(raw.get("completed", [])), "review": raw.get("review")}
    except (OSError, json.JSONDecodeError, TypeError):
        return {"completed": set(), "review": None}


def save_progress() -> None:
    if PUBLIC_MODE:
        return
    payload = {
        "completed": sorted(st.session_state.completed),
        "review": st.session_state.review,
    }
    PROGRESS_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def initialize() -> None:
    saved = load_progress()
    defaults = {
        "completed": saved["completed"],
        "review": saved["review"],
        "quiz_result": {},
        "practice_result": {},
        "free_result": None,
    }
    for name, default in defaults.items():
        if name not in st.session_state:
            st.session_state[name] = default


def normalize_output(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).casefold()


def normalize_table(frame: pd.DataFrame) -> list[tuple]:
    def clean(value):
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return round(float(value), 6)
        return str(value).strip()

    return sorted(tuple(clean(value) for value in row) for row in frame.itertuples(index=False, name=None))


def dax_example_result(index: int, region: str):
    """Resultado didáctico con pandas; no interpreta expresiones DAX arbitrarias."""
    sales = pd.read_csv(DATA / "ventas.csv")
    sales["ingreso"] = sales["unidades"] * sales["precio"]
    current = sales if region == "Todas" else sales[sales["region"] == region]
    revenue = current["ingreso"].sum()
    if index == 0:
        return len(current)
    if index == 1:
        return current["precio"].sum()
    if index == 2:
        return revenue
    if index == 3:
        return current[["producto", "unidades", "precio", "ingreso"]].head(8)
    if index == 4:
        return round(revenue / len(current), 2) if len(current) else 0
    if index == 5:
        return sales.loc[sales["region"] == "Sur", "ingreso"].sum()
    if index == 6:
        return current.loc[current["categoria"] == "Papeleria", "ingreso"].sum()
    if index == 7:
        return round(100 * revenue / sales["ingreso"].sum(), 2)
    if index == 8:
        return current["region"].nunique()
    if index == 9:
        return round(revenue * 1.10, 2)
    if index == 10:
        ranking = current.groupby("producto", as_index=False)["ingreso"].sum().sort_values("ingreso", ascending=False)
        ranking["ranking"] = ranking["ingreso"].rank(method="min", ascending=False).astype(int)
        return ranking
    monthly = current.assign(mes=current["fecha"].str[:7]).groupby("mes", as_index=False)["ingreso"].sum().sort_values("mes")
    monthly["acumulado"] = monthly["ingreso"].cumsum()
    return monthly


def execute_lesson(route: str, code: str, lesson: dict) -> dict:
    solution = lesson["solution"]
    if route == "Python":
        result = run_python(code)
        if result["error"]:
            return {**result, "passed": False, "feedback": "Corrige el error y vuelve a ejecutar."}
        reference = run_python(solution)
        passed = bool(result["images"]) if lesson["check"] == "plot" else normalize_output(result["stdout"]) == normalize_output(reference["stdout"])
        feedback = "¡Resultado correcto!" if passed else "Se ejecutó. El resultado difiere del esperado; revisa el reto o compara con la solución."
        return {**result, "passed": passed, "feedback": feedback}
    if route == "SQL":
        result = run_sql(code)
        if result["error"]:
            return {**result, "passed": False, "feedback": "Corrige la consulta y vuelve a ejecutarla."}
        expected = run_sql(solution)
        table, reference = result["table"], expected["table"]
        passed = table is not None and reference is not None and table.shape[1] == reference.shape[1] and normalize_table(table) == normalize_table(reference)
        feedback = "¡Resultado correcto!" if passed else "La consulta se ejecutó, pero los valores no coinciden con el reto."
        return {**result, "passed": passed, "feedback": feedback}
    if route == "R":
        if not find_rscript():
            equivalent = re.sub(r"\s+", "", code).casefold() == re.sub(r"\s+", "", solution).casefold()
            feedback = "La solución escrita coincide con la propuesta. Instala R para ejecutarla y observar el resultado." if equivalent else "R aún no está instalado; compara tu código con la solución propuesta."
            return {"stdout": "", "error": "", "images": [], "passed": equivalent, "feedback": feedback}
        result = run_r(code)
        if result["error"]:
            return {**result, "passed": False, "feedback": "Revisa el mensaje de R."}
        reference = run_r(solution)
        passed = bool(result["images"]) if lesson["check"] == "plot" else normalize_output(result["stdout"]) == normalize_output(reference["stdout"])
        feedback = "¡Resultado correcto!" if passed else "Se ejecutó. Compara el resultado con la solución propuesta."
        return {**result, "passed": passed, "feedback": feedback}
    passed, feedback = check_dax(code, solution)
    return {"passed": passed, "feedback": feedback, "error": ""}


def show_execution(route: str, result: dict) -> None:
    if result.get("error"):
        st.error(result["error"])
    if route in {"Python", "R"}:
        if result.get("stdout"):
            st.code(result["stdout"], language="text")
        for image in result.get("images", []):
            st.image(image, caption="Gráfica creada con tu código")
    elif route == "SQL":
        if result.get("message"):
            st.caption(result["message"])
        if result.get("table") is not None:
            st.dataframe(result["table"], hide_index=True)
    if "feedback" in result:
        (st.success if result.get("passed") else st.info)(result["feedback"])


def home() -> None:
    st.markdown(
        '<div class="hero"><span>CURSO INTERACTIVO</span><h1>DataLab</h1>'
        '<p>Aprende a programar y analizar datos desde cero. Escribe, ejecuta, observa y corrige.</p></div>',
        unsafe_allow_html=True,
    )
    total = sum(len(route["lessons"]) for route in CURRICULUM.values())
    a, b, c = st.columns(3)
    a.metric("Lecciones", total)
    b.metric("Programas", len(CURRICULUM))
    c.metric("Completadas", len(st.session_state.completed))
    st.subheader("Elige tu ruta")
    columns = st.columns(4)
    for column, (name, route) in zip(columns, CURRICULUM.items()):
        with column, st.container(border=True):
            st.subheader(f"{route['icon']} {name}")
            st.write(route["description"])
            done = sum(f"{name}:{i}" in st.session_state.completed for i in range(len(route["lessons"])))
            st.progress(done / len(route["lessons"]))
            st.caption(f"{done} de {len(route['lessons'])} lecciones")
    st.subheader("Cómo se estudia")
    st.write("Cada tema incluye una explicación, un ejemplo, un reto para escribir desde cero, un editor, resultados visibles, una solución y una pregunta de repaso.")
    if PUBLIC_MODE:
        st.info("Python, SQL y R se ejecutan en tu navegador. La primera ejecución descarga el entorno; después puedes practicar en línea.")
    st.info("Ruta sugerida: Introducción → Básico → Intermedio → Avanzado. Puedes cambiar de programa o nivel cuando quieras.")


def lessons() -> None:
    st.title("Aprender y practicar")
    route = st.selectbox("Programa", list(CURRICULUM), key="learn_route")
    level = st.selectbox("Nivel", LEVELS, key=f"learn_level_{route}")
    course = CURRICULUM[route]
    indices = [i for i, item in enumerate(course["lessons"]) if item["level"] == level]
    index = st.selectbox("Tema", indices, format_func=lambda value: course["lessons"][value]["title"], key=f"learn_topic_{route}_{level}")
    item = course["lessons"][index]
    lesson_key = f"{route}:{index}"
    language = {"Python": "python", "SQL": "sql", "R": "r", "Power BI + DAX": "text"}[route]
    if PUBLIC_MODE and route == "R":
        st.caption("R se carga en tu navegador con WebR. Los módulos iniciales usan R base; dplyr y ggplot2 se descargan al necesitarlos.")
    else:
        st.caption(course["setup"])
    st.header(item["title"])
    st.markdown(f"**Nivel:** {level} · **Tema {index + 1} de {len(course['lessons'])}**")
    st.write(item["concept"])
    with st.expander("Ver ejemplo guiado", expanded=True):
        st.code(item["example"], language=language)

    st.subheader("Tu reto")
    st.write(item["task"])
    editor_key = f"editor_{route}_{index}"
    left, right = st.columns([1, 1])
    with left:
        if st.button("Cargar ejemplo en el editor", key=f"load_{lesson_key}"):
            st.session_state[editor_key] = item["example"]
    with right:
        if st.button("Limpiar editor", key=f"clear_{lesson_key}"):
            st.session_state[editor_key] = ""
    with st.form(f"practice_{lesson_key}"):
        code = st.text_area("Escribe el código desde cero", key=editor_key, height=230, placeholder="Empieza a escribir aquí…")
        submitted = st.form_submit_button("Ejecutar y comprobar" if route != "Power BI + DAX" else "Comprobar fórmula")
    if submitted:
        if PUBLIC_MODE and route != "Power BI + DAX":
            st.session_state.practice_result[lesson_key] = {"code": code, "browser": True}
        else:
            result = execute_lesson(route, code, item)
            st.session_state.practice_result[lesson_key] = {"code": code, "result": result}
    saved = st.session_state.practice_result.get(lesson_key)
    if saved and saved["code"] == code:
        st.markdown("**Resultado de tu práctica**")
        if saved.get("browser"):
            show_browser_result(route, code, item["solution"], item["check"])
        else:
            show_execution(route, saved["result"])
        if route == "Power BI + DAX" and saved["result"].get("passed"):
            st.markdown("**Vista previa con los datos de ejemplo**")
            region = st.selectbox("Simular filtro de región", ["Todas", "Norte", "Sur", "Centro", "Oeste"], key=f"dax_region_{index}")
            preview = dax_example_result(index, region)
            if isinstance(preview, pd.DataFrame):
                st.dataframe(preview, hide_index=True)
            else:
                st.metric("Resultado esperado", f"{preview:,.2f}" if isinstance(preview, float) else f"{preview:,}")
            st.caption("Esta vista previa se calcula con Python para explicar el ejercicio; ejecuta la medida DAX en Power BI para comprobar su comportamiento real.")
    if route == "R" and not PUBLIC_MODE and not find_rscript():
        st.caption("R aún no se detecta en este equipo. Puedes escribir tu solución; instala R para ejecutarla aquí.")
    if route == "Power BI + DAX":
        st.caption("La comprobación compara la fórmula de este ejercicio. Ejecuta DAX en Power BI Desktop para explorar el contexto de filtro real.")
    with st.expander("Pista y solución propuesta"):
        st.code(item["solution"], language=language)

    st.subheader("Pregunta de repaso")
    with st.form(f"quiz_{lesson_key}"):
        choice = st.radio(item["question"], ["Selecciona una respuesta", *item["options"]], key=f"quiz_choice_{lesson_key}")
        checked = st.form_submit_button("Comprobar respuesta")
    if checked:
        correct = choice == item["answer"]
        st.session_state.quiz_result[lesson_key] = correct
        if correct:
            st.session_state.completed.add(lesson_key)
            save_progress()
    if lesson_key in st.session_state.quiz_result:
        if st.session_state.quiz_result[lesson_key]:
            st.success("Respuesta correcta. Lección registrada en tu progreso.")
        else:
            st.warning("Vuelve a revisar el concepto y prueba otra vez.")


def free_lab() -> None:
    st.title("Laboratorio libre")
    st.write("Prueba código propio. El editor comienza vacío; puedes consultar las bases de ejemplo desde la sección Datos.")
    route = st.selectbox("Lenguaje", list(CURRICULUM), key="free_route")
    if route == "SQL":
        with st.expander("Tablas disponibles"):
            for name in ("ventas", "clientes", "pedidos", "estudiantes"):
                frame = pd.read_csv(DATA / f"{name}.csv")
                st.write(f"**{name}**: {', '.join(frame.columns)}")
    if route == "Python" and not PUBLIC_MODE:
        st.caption("Tu código se ejecuta localmente con tus permisos. Usa código propio o que entiendas.")
    if route == "R" and not PUBLIC_MODE and not find_rscript():
        st.info("Para ejecutar R en este laboratorio, instala R. Los ejemplos y el editor siguen disponibles.")
    with st.form(f"free_form_{route}"):
        code = st.text_area("Tu código", key=f"free_code_{route}", height=300, placeholder="Escribe aquí…")
        submitted = st.form_submit_button("Ejecutar" if route != "Power BI + DAX" else "Analizar fórmula")
    if submitted:
        if PUBLIC_MODE and route != "Power BI + DAX":
            st.session_state.free_result = {"route": route, "code": code, "browser": True}
        elif route == "Python":
            result = run_python(code)
        elif route == "SQL":
            result = run_sql(code)
        elif route == "R":
            result = run_r(code)
        else:
            balanced = code.count("(") == code.count(")")
            found = re.findall(r"\b[A-Z][A-Z0-9_]+(?=\s*\()", code.upper())
            result = {"error": "" if balanced else "Los paréntesis no están equilibrados.", "feedback": "Funciones detectadas: " + (", ".join(dict.fromkeys(found)) or "ninguna") + ". Para calcular el resultado, usa Power BI Desktop."}
        if not (PUBLIC_MODE and route != "Power BI + DAX"):
            st.session_state.free_result = {"route": route, "code": code, "result": result}
    saved = st.session_state.free_result
    if saved and saved["route"] == route and saved["code"] == code:
        if saved.get("browser"):
            show_browser_result(route, code)
        else:
            show_execution(route, saved["result"])


def visuals() -> None:
    st.title("Creador de gráficas y objetos visuales")
    st.write("Elige una base, filtra registros y construye una gráfica. También puedes cargar tu propio CSV.")
    source = st.selectbox("Base de ejemplo", ["ventas", "estudiantes", "pedidos", "clientes"])
    upload = st.file_uploader("O carga un archivo CSV", type="csv")
    if PUBLIC_MODE and upload is not None and upload.size > 2_000_000:
        st.error("El CSV supera el límite de 2 MB para la versión pública.")
        return
    try:
        frame = pd.read_csv(upload) if upload else pd.read_csv(DATA / f"{source}.csv")
    except Exception as exc:
        st.error(f"No se pudo leer el CSV: {exc}")
        return
    if frame.empty:
        st.warning("El archivo no contiene filas.")
        return
    if {"unidades", "precio"}.issubset(frame.columns):
        frame["ingreso"] = pd.to_numeric(frame["unidades"], errors="coerce") * pd.to_numeric(frame["precio"], errors="coerce")
    categories = [column for column in frame if frame[column].nunique(dropna=True) <= 20 or frame[column].dtype == object]
    numbers = list(frame.select_dtypes(include="number").columns)
    if not categories or not numbers:
        st.warning("Para construir gráficas se necesita una columna categórica y una numérica.")
        st.dataframe(frame, hide_index=True)
        return
    default_dim = "region" if "region" in categories else categories[0]
    dimension = st.selectbox("Categoría o eje", categories, index=categories.index(default_dim))
    measure = st.selectbox("Medida numérica", numbers, index=numbers.index("ingreso") if "ingreso" in numbers else 0)
    values = sorted(frame[dimension].dropna().unique().tolist(), key=str)
    selected = st.multiselect("Filtrar valores", values, default=values)
    filtered = frame[frame[dimension].isin(selected)].copy()
    if filtered.empty:
        st.warning("No hay filas con estos filtros.")
        return
    aggregation = st.selectbox("Cálculo", ["Suma", "Promedio", "Conteo"])
    visual = st.selectbox("Objeto visual", ["Barras", "Línea", "Área", "Dispersión", "Tabla"])
    numeric = pd.to_numeric(filtered[measure], errors="coerce")
    a, b, c = st.columns(3)
    a.metric("Registros", len(filtered))
    b.metric(f"Total de {measure}", f"{numeric.sum():,.2f}")
    c.metric(f"Promedio de {measure}", f"{numeric.mean():,.2f}")
    if visual == "Dispersión":
        x = st.selectbox("Eje X", numbers, index=0)
        y = st.selectbox("Eje Y", numbers, index=numbers.index(measure))
        st.scatter_chart(filtered, x=x, y=y, color=dimension)
    elif visual == "Tabla":
        st.dataframe(filtered, hide_index=True)
    else:
        grouped = filtered.groupby(dimension, dropna=False)[measure].agg({"Suma": "sum", "Promedio": "mean", "Conteo": "count"}[aggregation]).reset_index(name="valor")
        if visual == "Barras":
            st.bar_chart(grouped, x=dimension, y="valor")
        elif visual == "Línea":
            st.line_chart(grouped, x=dimension, y="valor")
        else:
            st.area_chart(grouped, x=dimension, y="valor")
        st.dataframe(grouped, hide_index=True)
    st.download_button("Descargar datos filtrados", filtered.to_csv(index=False).encode("utf-8-sig"), file_name="datos_filtrados.csv", mime="text/csv")
    with st.expander("Código Python para reproducir el resumen"):
        function = {"Suma": "sum", "Promedio": "mean", "Conteo": "count"}[aggregation]
        st.code(f"import pandas as pd\ndatos = pd.read_csv('data/{source}.csv')\nresumen = datos.groupby('{dimension}')['{measure}'].{function}()\nprint(resumen)", language="python")


def datasets() -> None:
    st.title("Bases de datos")
    st.write("Descarga los archivos y úsalos en los ejercicios de cada programa. Todos los registros son ficticios.")
    names = ("ventas", "clientes", "pedidos", "estudiantes")
    tabs = st.tabs([*names, "SQLite"])
    for tab, name in zip(tabs[:4], names):
        with tab:
            frame = pd.read_csv(DATA / f"{name}.csv")
            st.caption(f"{len(frame)} filas · {len(frame.columns)} columnas")
            st.dataframe(frame, hide_index=True)
            st.download_button(f"Descargar {name}.csv", (DATA / f"{name}.csv").read_bytes(), file_name=f"{name}.csv", mime="text/csv", key=f"download_{name}")
    with tabs[4]:
        st.write("La base SQLite contiene las cuatro tablas.")
        st.download_button("Descargar curso.sqlite", (DATA / "curso.sqlite").read_bytes(), file_name="curso.sqlite", mime="application/vnd.sqlite3")


def review() -> None:
    st.title("Repaso general")
    st.write("Ocho preguntas cubren los conceptos principales del curso.")
    with st.form("review_form"):
        choices = [st.radio(f"{i+1}. {question}", ["Selecciona una respuesta", *options], key=f"review_{i}") for i, (question, options, _answer) in enumerate(REVIEW)]
        submitted = st.form_submit_button("Calificar")
    if submitted:
        st.session_state.review = sum(choice == answer for choice, (_question, _options, answer) in zip(choices, REVIEW))
        save_progress()
    if st.session_state.review is not None:
        st.metric("Resultado", f"{st.session_state.review}/{len(REVIEW)}")
        with st.expander("Revisar respuestas"):
            for i, (_question, _options, answer) in enumerate(REVIEW, 1):
                st.write(f"{i}. {answer}")
    st.subheader("Proyecto integrador")
    st.write("Analiza ingresos por región con SQL y Python, crea una visualización en R y reproduce el indicador como medida DAX en Power BI. Explica qué cambia al filtrar una categoría.")


def main() -> None:
    st.set_page_config(page_title="DataLab · Curso interactivo", page_icon="📚", layout="wide")
    st.markdown(
        """<style>
        .block-container {max-width: 1160px; padding-top: 1.6rem}
        .hero {background: linear-gradient(115deg,#083344,#155e75 60%,#0e7490);
               border-radius: 18px; padding: 2.2rem; color: white; margin-bottom: 1rem}
        .hero h1 {color: white; font-size: 3rem; margin: .2rem 0}
        .hero p {color: #e0f2fe; font-size: 1.1rem}
        .hero span {letter-spacing: .13em; font-size: .78rem; font-weight: 700}
        </style>""",
        unsafe_allow_html=True,
    )
    initialize()
    pages = {
        "Inicio": home,
        "Aprender": lessons,
        "Laboratorio libre": free_lab,
        "Visualizaciones": visuals,
        "Bases de datos": datasets,
        "Repaso": review,
    }
    with st.sidebar:
        st.title("📚 DataLab")
        page = st.radio("Ir a", list(pages))
        st.divider()
        total = sum(len(route["lessons"]) for route in CURRICULUM.values())
        st.write(f"**Progreso:** {len(st.session_state.completed)} de {total} lecciones")
        st.progress(len(st.session_state.completed) / total)
        st.caption("El progreso dura mientras esta sesión esté abierta." if PUBLIC_MODE else "El progreso se guarda en este equipo.")
    pages[page]()


if __name__ == "__main__":
    main()
