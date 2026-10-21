from agents import Agent
from agents.mcp import MCPServerStdio

from .system_prompt import build_agent_instructions


def create_agent(yazio_mcp: MCPServerStdio) -> Agent[None]:
    """Construit l'agent et lui injecte le serveur MCP YAZIO."""
    return Agent(
        name="Assistant Yazio",
        instructions=build_agent_instructions,
        mcp_servers=[yazio_mcp],
    )
