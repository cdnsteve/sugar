"""
TOON (Token-Oriented Object Notation) encoder for Sugar.

TOON is a compact data format designed for LLMs that reduces token usage
by 30-60% compared to JSON for tabular data.

Reference: https://github.com/toon-format/toon
"""

from typing import Any, Dict, List, Optional


def to_toon(
    data: List[Dict[str, Any]],
    name: str = "items",
    max_field_width: Optional[int] = None,
) -> str:
    """
    Convert a list of dictionaries to TOON format.

    TOON declares field names once (like CSV headers) instead of repeating them,
    resulting in significant token savings for tabular data.

    Args:
        data: List of dictionaries with uniform keys
        name: Name for the collection
        max_field_width: Optional max width for field values (truncates with ...)

    Returns:
        TOON-formatted string

    Example:
        >>> data = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
        >>> print(to_toon(data, "users"))
        users[2]{id,name}:
          1,Alice
          2,Bob
    """
    if not data:
        return f"{name}[0]{{}}:"

    # Get fields from first item (assumes uniform structure)
    fields = list(data[0].keys())
    field_str = ",".join(fields)

    # Build rows
    rows = []
    for item in data:
        values = []
        for f in fields:
            val = str(item.get(f, ""))
            # Escape commas in values
            if "," in val:
                val = f'"{val}"'
            # Truncate if needed
            if max_field_width and len(val) > max_field_width:
                val = val[: max_field_width - 3] + "..."
            values.append(val)
        rows.append("  " + ",".join(values))

    return f"{name}[{len(data)}]{{{field_str}}}:\n" + "\n".join(rows)


def execution_history_to_toon(history: List[Dict[str, Any]]) -> str:
    """
    Convert execution history to TOON format for context injection.

    Args:
        history: List of execution history entries

    Returns:
        TOON-formatted execution history
    """
    if not history:
        return "history[0]{}:"

    simplified = [
        {
            "task": str(h.get("title", ""))[:50],
            "status": "ok" if h.get("success") else "fail",
            "files": len(h.get("files_modified", [])),
            "time": f"{h.get('execution_time', 0):.0f}s",
        }
        for h in history
    ]
    return to_toon(simplified, "history")


def work_queue_to_toon(tasks: List[Dict[str, Any]]) -> str:
    """
    Convert work queue to TOON format for context injection.

    Args:
        tasks: List of work queue tasks

    Returns:
        TOON-formatted work queue
    """
    if not tasks:
        return "queue[0]{}:"

    simplified = [
        {
            "id": str(t.get("id", ""))[:8],
            "type": str(t.get("type", "")),
            "title": str(t.get("title", ""))[:40],
            "pri": t.get("priority", 3),
        }
        for t in tasks
    ]
    return to_toon(simplified, "queue")


def files_to_toon(files: List[str], action: str = "modified") -> str:
    """
    Convert file list to TOON format.

    Args:
        files: List of file paths
        action: Action performed on files

    Returns:
        TOON-formatted file list
    """
    if not files:
        return "files[0]{}:"

    data = [{"path": f, "action": action} for f in files]
    return to_toon(data, "files")


def quality_results_to_toon(results: List[Dict[str, Any]]) -> str:
    """
    Convert quality gate results to TOON format.

    Args:
        results: List of quality gate check results

    Returns:
        TOON-formatted quality results
    """
    if not results:
        return "checks[0]{}:"

    simplified = [
        {
            "check": str(r.get("name", ""))[:20],
            "status": "pass" if r.get("passed") else "fail",
            "msg": str(r.get("message", ""))[:30],
        }
        for r in results
    ]
    return to_toon(simplified, "checks")


# Convenience function for any dict list
def encode(data: List[Dict[str, Any]], name: str = "data") -> str:
    """Alias for to_toon() for cleaner imports."""
    return to_toon(data, name)
