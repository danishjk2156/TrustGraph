from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models import *  # noqa: F401,F403
from trust_scorer import TrustScorer  # noqa: F401
from visualization import install_cognee_visualizer, visualize_graph  # noqa: F401

try:
    from trust_memory import TrustMemory  # noqa: F401
except Exception:  # pragma: no cover
    TrustMemory = None

install_cognee_visualizer()

__all__ = [
    "TrustMemory",
    "TrustScorer",
    "install_cognee_visualizer",
    "visualize_graph",
]
