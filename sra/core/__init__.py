"""Core primitives: RunContext, ports (protocols), errors, and the agent state enum.

Every other package depends on `core` and `models`; `core` depends on nothing
internal except `models`. This keeps the dependency graph acyclic.
"""
