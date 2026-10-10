"""Punto de entrada para Streamlit Community Cloud."""

import os

os.environ["DATALAB_PUBLIC_MODE"] = "1"

from app import main


if __name__ == "__main__":
    main()
