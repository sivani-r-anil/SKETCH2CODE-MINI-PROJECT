
import sys
from pathlib import Path

# Permanent pure-Python bidi dependency
BACKEND_DIR = Path(__file__).resolve().parent
BIDI_DIR = BACKEND_DIR / "compat_deps"

if not (BIDI_DIR / "bidi" / "algorithm.py").exists():
    raise RuntimeError(
        "Pure-Python bidi dependency not found in compat_deps."
    )

# Prioritize the compatible Python implementation
sys.path.insert(0, str(BIDI_DIR))

import bidi
from bidi.algorithm import get_display

# Make the function available to EasyOCR
bidi.get_display = get_display

# Load the existing FastAPI application
from main import app
