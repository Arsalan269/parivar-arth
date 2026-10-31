"""
Parivar Arth - Main entrypoint forwarder to app/Login.py.
Ensures seamless compatibility with Streamlit Cloud deployments configured with app/main.py.
"""

import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.Login import main

if __name__ == "__main__":
    main()
