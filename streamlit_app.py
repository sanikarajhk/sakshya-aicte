"""
Sakshya Streamlit Community Cloud Entry Point
SIH 2026 - Problem Statement SIH26261: AI-Powered Application Validation for AICTE
"""

import sys
from pathlib import Path
import runpy

# Ensure repository root is in sys.path
REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Delegate execution to the main dashboard application
dashboard_app = REPO_ROOT / "sakshya" / "dashboard" / "app.py"
runpy.run_path(str(dashboard_app), run_name="__main__")
