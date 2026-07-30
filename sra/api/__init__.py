"""FastAPI application: thin HTTP surface over the application service.
Contains no agent logic.
"""

from sra.api.app import create_app

__all__ = ["create_app"]
