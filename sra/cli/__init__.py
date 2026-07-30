"""CLI entrypoint: wraps the same application service as the API."""

from sra.cli.main import app, main

__all__ = ["app", "main"]
