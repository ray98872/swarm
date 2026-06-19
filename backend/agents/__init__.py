"""Specialist sub-agents for the Swarm research system."""

from .base import BaseAgent
from .benchmark import BenchmarkAgent
from .community import CommunityAgent
from .docs import DocsAgent
from .risk import RiskAgent
from .web_search import WebSearchAgent

# The retrieval swarm, in display order. The orchestrator fans out over this list.
SUB_AGENTS: list[type[BaseAgent]] = [
    WebSearchAgent,
    DocsAgent,
    BenchmarkAgent,
    CommunityAgent,
    RiskAgent,
]

__all__ = [
    "BaseAgent",
    "WebSearchAgent",
    "DocsAgent",
    "BenchmarkAgent",
    "CommunityAgent",
    "RiskAgent",
    "SUB_AGENTS",
]
