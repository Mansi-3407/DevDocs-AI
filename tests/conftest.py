"""
Shared pytest configuration.

Adds the repository root to sys.path so that ``app.*`` imports work without
requiring an editable install.
"""
import sys
from pathlib import Path

# Repository root  = tests/../
_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
