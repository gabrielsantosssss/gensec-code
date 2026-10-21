# Gabriel Santos Z23667113 — COT 4930 HW4
"""Multi-server MCP agent for investigating an SSH brute-force attack.

This LangChain agent connects to two stdio MCP servers at the same time:

1. ssh_log_analyzer: the custom server in mcp-server.py, which parses
   OpenSSH auth logs (failed/accepted logins, top offenders, possible
   compromises, timeframe summary).
2. filesystem: the official @modelcontextprotocol/server-filesystem server,
   scoped to this file's directory, used to read allowlist.txt and write
   incident_report.md.

A Gemini model (via langchain_google_genai) coordinates the tools from both
servers to analyze sample_auth.log, compare offending IPs against the
allowlist, and write a Markdown incident report.

Requires GOOGLE_API_KEY in the environment; GOOGLE_MODEL optionally
overrides the default model.
"""

import asyncio
import os
import sys

from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mcp_adapters.client import MultiServerMCPClient

# Directory containing this file; both servers run here so relative paths
# like sample_auth.log and allowlist.txt resolve correctly.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_PATH = os.path.join(BASE_DIR, "incident_report.md")

TASK = (
    "You are a security analyst. The SSH auth log is at sample_auth.log and a "
    "known-good source-IP allowlist is at allowlist.txt (one IP per line, '#' "
    "comments). (1) Find the top offending source IPs and the usernames they "
    "targeted; (2) identify any IP that logged in successfully after repeated "
    "failures (possible compromise); (3) read allowlist.txt and determine which "
    "offending IPs are NOT on the allowlist; (4) write a concise Markdown "
    "incident report to incident_report.md with the findings, the unauthorized "
    "IPs, the possible compromise, and recommended remediation steps."
)


async def main() -> None:
    """Connect to both MCP servers, run the investigation, and print results."""
    # The Google SDK reads GOOGLE_API_KEY on its own; just fail early if missing.
    if not os.environ.get("GOOGLE_API_KEY"):
        print("GOOGLE_API_KEY is not set. Run: export GOOGLE_API_KEY=<your key>")
        sys.exit(1)

    # Launch both MCP servers as stdio subprocesses.
    client = MultiServerMCPClient(
        {
            "ssh_log_analyzer": {
                # uv run ensures the project venv (with fastmcp) is used.
                "command": "uv",
                "args": ["run", "python", "mcp-server.py", "stdio"],
                "transport": "stdio",
                "cwd": BASE_DIR,
            },
            "filesystem": {
                # Access is restricted to this file's directory.
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", BASE_DIR],
                "transport": "stdio",
                "cwd": BASE_DIR,
            },
        }
    )

    # Collect the tools from both servers into one list for the agent.
    tools = await client.get_tools()
    print(f"Loaded {len(tools)} tools: {', '.join(t.name for t in tools)}\n")

    model = ChatGoogleGenerativeAI(
        model=os.environ.get("GOOGLE_MODEL", "gemini-flash-lite-latest")
    )
    agent = create_agent(model, tools)

    # The agent decides which tools to call, and in what order, to finish the task.
    result = await agent.ainvoke({"messages": [{"role": "user", "content": TASK}]})

    print("=== Agent response ===")
    print(result["messages"][-1].text)

    # Show the report the agent wrote through the filesystem server.
    if os.path.isfile(REPORT_PATH):
        print("\n=== incident_report.md ===")
        with open(REPORT_PATH, encoding="utf-8") as f:
            print(f.read())
    else:
        print("\nincident_report.md was not created.")


if __name__ == "__main__":
    asyncio.run(main())
