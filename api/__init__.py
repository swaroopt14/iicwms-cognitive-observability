"""
IICWMS API Layer — Production-Grade FastAPI Backend
"""

from .server import app
from .config import settings

__all__ = ["app", "settings"]
