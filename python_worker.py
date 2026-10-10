"""Proceso secundario para ejecutar el código Python escrito por el alumno.

Esta aplicación es local y de un solo usuario. El código se ejecuta con los
permisos de quien inició Streamlit; no es un sandbox para una web pública.
"""

from __future__ import annotations

import ast
import base64
import contextlib
import io
import json
import os
import sys
import traceback


os.environ["MPLBACKEND"] = "Agg"


def main() -> None:
    source = sys.stdin.read()
    output = io.StringIO()
    images: list[str] = []
    error = ""
    try:
        plotting = "matplotlib" in source or "plt." in source
        if plotting:
            import matplotlib.pyplot as plt

            def collect_figures(*_args, **_kwargs) -> None:
                for number in list(plt.get_fignums())[:3]:
                    figure = plt.figure(number)
                    buffer = io.BytesIO()
                    figure.savefig(buffer, format="png", bbox_inches="tight")
                    images.append(base64.b64encode(buffer.getvalue()).decode("ascii"))
                    plt.close(figure)

            plt.show = collect_figures
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            tree = ast.parse(source, filename="<tu_codigo>")
            namespace = {"__name__": "__main__"}
            if tree.body and isinstance(tree.body[-1], ast.Expr):
                last = tree.body.pop()
                exec(compile(tree, "<tu_codigo>", "exec"), namespace)
                value = eval(compile(ast.Expression(last.value), "<tu_codigo>", "eval"), namespace)
                if value is not None:
                    print(value)
            else:
                exec(compile(tree, "<tu_codigo>", "exec"), namespace)
            if plotting and plt.get_fignums():
                collect_figures()
    except Exception:
        error = traceback.format_exc(limit=5)
    payload = {"stdout": output.getvalue()[:20000], "error": error[:12000], "images": images}
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
