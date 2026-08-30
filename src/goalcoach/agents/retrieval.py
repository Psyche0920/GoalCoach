"""Retrieval Agent.

Retrieval order:
1. reuse cached material when suitable;
2. exact concept lookup in SQLite;
3. structured metadata filtering;
4. optional ChromaDB search for ambiguous semantic needs;
5. learner-specific re-ranking using errors and retention gaps.

TODO(interface): implement ``Retriever`` after licensed curriculum data exists and add
vector retrieval only if the benchmark shows value over structured lookup.
"""

from goalcoach.agents.interfaces import Retriever

__all__ = ["Retriever"]
