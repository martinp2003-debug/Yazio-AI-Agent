import os
import shlex

from agents.mcp import MCPServerStdio


def create_yazio_mcp_server() -> MCPServerStdio:
    """Prépare le processus MCP YAZIO, sans encore le démarrer."""
    command = os.getenv("YAZIO_MCP_COMMAND")
    raw_args = os.getenv("YAZIO_MCP_ARGS")
    cwd = os.getenv("YAZIO_MCP_CWD")

    missing_variables = [
        name
        for name, value in {
            "YAZIO_MCP_COMMAND": command,
            "YAZIO_MCP_ARGS": raw_args,
            "YAZIO_MCP_CWD": cwd,
        }.items()
        if not value
    ]
    if missing_variables:
        raise RuntimeError(
            "Configuration MCP incomplète : " + ", ".join(missing_variables)
        )

    return MCPServerStdio(
        name="MCP YAZIO",
        params={
            "command": command,
            "args": shlex.split(raw_args),
            "cwd": cwd,
        },
        cache_tools_list=True,
    )
