"""SSH log analyzer MCP server.

A FastMCP server named "ssh-log-analyzer" that exposes tools for analyzing
OpenSSH / syslog authentication logs (e.g. /var/log/auth.log) for signs of
SSH brute-force attacks. It parses three kinds of sshd messages:

    Failed password for <user> from <ip> ...
    Failed password for invalid user <user> from <ip> ...
    Accepted password for <user> from <ip> ...

Tools report failed-login events, top offending source IPs, the most targeted
usernames, IPs that succeeded after repeated failures (possible compromise),
and an overall timeframe summary. All parsing is done with Python's ``re``
module and plain file reading; no shell commands are executed.

Usage:
    python mcp-server.py [transport]

The transport is read from the first command-line argument and defaults to
"stdio".
"""

import re
import sys
from collections import Counter
from pathlib import Path

from fastmcp import FastMCP

mcp = FastMCP("ssh-log-analyzer")

# Classic syslog ("Oct 20 02:10:01") or RFC 3339 ("2026-10-20T02:10:01.123+00:00").
TIMESTAMP_RE = re.compile(
    r"^(?P<ts>[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}"
    r"|\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)"
)
FAILED_RE = re.compile(
    r"Failed password for (?P<invalid>invalid user )?(?P<user>\S+) from (?P<ip>\S+)"
)
ACCEPTED_RE = re.compile(r"Accepted password for (?P<user>\S+) from (?P<ip>\S+)")


def _validate_logpath(logpath: str) -> str | None:
    """Check that logpath exists and is a regular file.

    Args:
        logpath: Path to the log file supplied by the caller.

    Returns:
        An error message if the path is invalid, otherwise None.
    """
    path = Path(logpath)
    if not path.exists():
        return f"Log file not found: {logpath}"
    if not path.is_file():
        return f"Not a regular file: {logpath}"
    return None


def _read_lines(logpath: str) -> list[str]:
    """Read a log file into a list of lines, tolerating invalid UTF-8.

    Args:
        logpath: Path to an already-validated log file.

    Returns:
        The file's lines without trailing newlines.
    """
    with open(logpath, encoding="utf-8", errors="replace") as f:
        return f.read().splitlines()


def _timestamp(line: str) -> str | None:
    """Extract the leading syslog timestamp from a log line.

    Args:
        line: A single log line.

    Returns:
        The timestamp string, or None if the line has no recognizable timestamp.
    """
    match = TIMESTAMP_RE.match(line)
    return match.group("ts") if match else None


def _load(logpath: str) -> tuple[list[str] | None, dict | None]:
    """Validate and read a log file.

    Args:
        logpath: Path to the log file.

    Returns:
        A (lines, error) tuple; exactly one of the two is None.
    """
    error = _validate_logpath(logpath)
    if error:
        return None, {"error": error}
    try:
        return _read_lines(logpath), None
    except OSError as e:
        return None, {"error": f"Could not read {logpath}: {e}"}


def _failed_events(lines: list[str]) -> list[dict]:
    """Parse failed SSH password attempts from log lines.

    Args:
        lines: Lines of an auth log.

    Returns:
        A list of dicts with timestamp, username, source_ip, and invalid_user.
    """
    events = []
    for line in lines:
        match = FAILED_RE.search(line)
        if match:
            events.append(
                {
                    "timestamp": _timestamp(line),
                    "username": match.group("user"),
                    "source_ip": match.group("ip"),
                    "invalid_user": match.group("invalid") is not None,
                }
            )
    return events


@mcp.tool()
def list_available_logs(directory: str = ".") -> list[str] | dict:
    """List .log files in a directory.

    Args:
        directory: Directory to search (non-recursive). Defaults to the
            current working directory.

    Returns:
        A sorted list of paths to .log files, or {"error": ...} if the
        directory does not exist or is not a directory.
    """
    path = Path(directory)
    if not path.exists():
        return {"error": f"Directory not found: {directory}"}
    if not path.is_dir():
        return {"error": f"Not a directory: {directory}"}
    return sorted(str(p) for p in path.glob("*.log") if p.is_file())


@mcp.tool()
def parse_failed_ssh(logpath: str) -> list[dict] | dict:
    """Parse failed SSH password login attempts from an auth log.

    Matches both "Failed password for <user> from <ip>" and
    "Failed password for invalid user <user> from <ip>" lines.

    Args:
        logpath: Path to an OpenSSH/syslog auth log file.

    Returns:
        A list of events, each a dict with keys timestamp, username,
        source_ip, and invalid_user (bool), or {"error": ...} if the file
        cannot be read.
    """
    lines, error = _load(logpath)
    if error:
        return error
    return _failed_events(lines)


@mcp.tool()
def top_offender_ips(logpath: str, n: int = 5) -> list[dict] | dict:
    """Rank source IPs by number of failed SSH logins.

    Args:
        logpath: Path to an OpenSSH/syslog auth log file.
        n: Maximum number of IPs to return. Defaults to 5.

    Returns:
        A list of {"ip", "failed_count"} dicts in descending order of
        failed_count, or {"error": ...} if the file cannot be read.
    """
    lines, error = _load(logpath)
    if error:
        return error
    counts = Counter(e["source_ip"] for e in _failed_events(lines))
    return [{"ip": ip, "failed_count": c} for ip, c in counts.most_common(max(n, 0))]


@mcp.tool()
def targeted_usernames(logpath: str, n: int = 5) -> list[dict] | dict:
    """Rank usernames by number of failed SSH logins targeting them.

    Args:
        logpath: Path to an OpenSSH/syslog auth log file.
        n: Maximum number of usernames to return. Defaults to 5.

    Returns:
        A list of {"username", "failed_count"} dicts in descending order of
        failed_count, or {"error": ...} if the file cannot be read.
    """
    lines, error = _load(logpath)
    if error:
        return error
    counts = Counter(e["username"] for e in _failed_events(lines))
    return [
        {"username": user, "failed_count": c} for user, c in counts.most_common(max(n, 0))
    ]


@mcp.tool()
def successful_after_failures(logpath: str, threshold: int = 3) -> list[dict] | dict:
    """Find source IPs that logged in successfully after repeated failures.

    An IP is flagged when an "Accepted password" line from it appears after
    at least `threshold` earlier failed logins from the same IP, which may
    indicate a successful brute-force compromise.

    Args:
        logpath: Path to an OpenSSH/syslog auth log file.
        threshold: Minimum number of prior failed logins required to flag
            an IP. Defaults to 3.

    Returns:
        A list of dicts with keys ip, failed_count (failures before the
        successful login), accepted_username, and accepted_timestamp, one
        per flagged IP, or {"error": ...} if the file cannot be read.
    """
    lines, error = _load(logpath)
    if error:
        return error
    failures: Counter[str] = Counter()
    flagged: dict[str, dict] = {}
    for line in lines:
        failed = FAILED_RE.search(line)
        if failed:
            failures[failed.group("ip")] += 1
            continue
        accepted = ACCEPTED_RE.search(line)
        if accepted:
            ip = accepted.group("ip")
            if ip not in flagged and failures[ip] >= threshold:
                flagged[ip] = {
                    "ip": ip,
                    "failed_count": failures[ip],
                    "accepted_username": accepted.group("user"),
                    "accepted_timestamp": _timestamp(line),
                }
    return list(flagged.values())


@mcp.tool()
def summarize_timeframe(logpath: str) -> dict:
    """Summarize the time span and authentication activity of an auth log.

    Args:
        logpath: Path to an OpenSSH/syslog auth log file.

    Returns:
        A dict with keys first_event and last_event (timestamps of the first
        and last timestamped lines, or None), total_lines, total_failed
        (failed password attempts), and total_accepted (accepted password
        logins), or {"error": ...} if the file cannot be read.
    """
    lines, error = _load(logpath)
    if error:
        return error
    timestamps = [ts for ts in map(_timestamp, lines) if ts]
    return {
        "first_event": timestamps[0] if timestamps else None,
        "last_event": timestamps[-1] if timestamps else None,
        "total_lines": len(lines),
        "total_failed": sum(1 for line in lines if FAILED_RE.search(line)),
        "total_accepted": sum(1 for line in lines if ACCEPTED_RE.search(line)),
    }


if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    mcp.run(transport=transport)
