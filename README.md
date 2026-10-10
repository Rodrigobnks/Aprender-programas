# DataLab

Plataforma para aprender **Python, SQL, R y Power BI/DAX** desde introducción hasta avanzado. Contiene 48 lecciones, editores vacíos para escribir desde cero, ejemplos, ejercicios, preguntas de repaso, bases de datos y un creador de gráficas.

## Abrir y compartir

- [Curso público en Streamlit](https://aprender-programas-rodrigobnks.streamlit.app/)
- [Código fuente en GitHub](https://github.com/Rodrigobnks/Aprender-programas)

La URL de Streamlit funciona desde otros equipos con conexión a Internet. Python, SQL y R ejecutan las prácticas en el navegador; el archivo `web_lab.html` se sirve mediante GitHub Pages para que WebR pueda iniciar desde una página HTTPS.

## Compartir con Streamlit Community Cloud

1. Publica esta carpeta en un repositorio de GitHub. No incluyas `.venv` ni `progreso.json`.
2. En [Streamlit Community Cloud](https://share.streamlit.io/), elige **Create app** y conecta el repositorio.
3. Selecciona la rama `main` y usa **`app_public.py`** como archivo principal. Este punto de entrada es necesario para la edición pública.
4. Activa GitHub Pages desde la rama `main` y la carpeta raíz. Si usas otro repositorio, cambia `RUNNER_URL` en `browser_lab.py` por la dirección de su `web_lab.html` publicado en Pages.
5. Streamlit instalará las dependencias de `requirements.txt` y entregará una URL `https://...streamlit.app` que puedes compartir.

En la edición pública, Python se ejecuta con Pyodide, SQL con sql.js y R con WebR dentro del navegador del visitante. La primera ejecución descarga los motores y, cuando se requieren, paquetes como pandas, matplotlib, dplyr o ggplot2. Se necesita conexión a Internet. Las soluciones se comparan en el mismo navegador. El progreso dura durante la sesión abierta; no hay cuentas ni sincronización entre dispositivos. DAX se comprueba como fórmula y muestra una vista previa didáctica: su motor real sigue siendo Power BI.

## Abrir la plataforma en este equipo

En PowerShell:

```powershell
Set-Location -LiteralPath 'C:\Users\EQUIPO\Desktop\datalab'
& 'C:\Users\EQUIPO\.venv\Scripts\python.exe' -m pip install -r .\requirements.txt
& 'C:\Users\EQUIPO\.venv\Scripts\python.exe' -m streamlit run .\app.py
```

Abre la dirección local que muestre Streamlit, normalmente `http://localhost:8501`. Si ya tienes la aplicación abierta, actualiza la página para cargar los cambios. Para detenerla, presiona `Ctrl+C` en PowerShell.

Si usas otro equipo, crea primero un entorno dentro de la carpeta con `py -3 -m venv .venv` y sustituye la ruta del intérprete por `.\.venv\Scripts\python.exe`.

## Cómo estudiar

1. En **Aprender**, elige un programa, nivel y tema.
2. Lee el concepto y el ejemplo. El editor del reto empieza vacío.
3. Escribe tu solución y pulsa **Ejecutar y comprobar**.
4. Revisa el resultado, la gráfica o el mensaje de error. Después responde la pregunta de repaso.
5. Usa **Laboratorio libre** para probar ideas sin un reto fijo.

Los niveles son **Introducción, Básico, Intermedio y Avanzado**. Cada programa tiene 12 lecciones. El creador de visualizaciones permite elegir una base, filtros, medida, cálculo y tipo de gráfica; también acepta CSV propios.

## Qué se ejecuta en la plataforma

- **Python:** ejecuta el código que escribes en un proceso local con un límite de 30 segundos. Captura texto y gráficas de Matplotlib. El código tiene acceso a tu equipo con los permisos de tu usuario: úsalo solo en esta instalación local y ejecuta código que conozcas.
- **SQL:** ejecuta consultas sobre una copia temporal en memoria de los datos. Puedes practicar SELECT, JOIN, CTE y funciones de ventana sin modificar los CSV originales.
- **R:** se ejecuta si `Rscript` está instalado. Si no lo está, puedes escribir y comparar con la solución propuesta. Instala R desde [CRAN](https://cran.r-project.org/) y, para las lecciones que lo usan, ejecuta en R `install.packages(c('dplyr', 'ggplot2'))`.
- **DAX:** el editor comprueba la fórmula propuesta y muestra una vista previa didáctica calculada con los datos del curso. DAX necesita Power BI Desktop para ejecutar medidas y observar su contexto de filtro real; esta aplicación no contiene el motor de Power BI.

En la edición local, el progreso se guarda en `progreso.json` dentro de esta carpeta.

## Datos incluidos

- `ventas.csv`: operaciones con fecha, región, producto, unidades y precio.
- `clientes.csv` y `pedidos.csv`: tablas relacionadas por `cliente_id`.
- `estudiantes.csv`: horas de estudio, asistencia y puntajes para estadística.
- `curso.sqlite`: las cuatro tablas en una base SQLite descargable.

Para regenerar la base SQLite después de editar los CSV:

```powershell
& 'C:\Users\EQUIPO\.venv\Scripts\python.exe' .\create_db.py
```

## Archivos principales

```text
app.py            Interfaz y navegación
app_public.py     Entrada para despliegue público
browser_lab.py    Construye el laboratorio de navegador
web_lab.html      Ejecución en el navegador
curriculum.py     Contenido de las 48 lecciones
runtime.py        Ejecución y comprobación de prácticas
python_worker.py  Proceso local para código Python
data/             Bases de ejemplo
```
