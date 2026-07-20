"""Tool system: the Tool protocol, ToolRegistry, and tool implementations
(search, website reader, PDF/HTML/Markdown readers, calculator, summarizer, ...).

Tools are plugins: register them; never special-case them in the runtime.
"""

from sra.tools.bootstrap import create_default_registry
from sra.tools.registry import InMemoryToolRegistry

__all__ = [
    "InMemoryToolRegistry",
    "create_default_registry",
]
