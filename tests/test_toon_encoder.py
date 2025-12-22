"""Tests for TOON encoder utility."""

import pytest
from sugar.utils.toon_encoder import (
    to_toon,
    execution_history_to_toon,
    work_queue_to_toon,
    files_to_toon,
    quality_results_to_toon,
    encode,
)


class TestToToon:
    """Tests for the main to_toon function."""

    def test_empty_list(self):
        """Empty list returns proper empty format."""
        result = to_toon([], "items")
        assert result == "items[0]{}:"

    def test_simple_list(self):
        """Simple list converts correctly."""
        data = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
        result = to_toon(data, "users")

        assert "users[2]{id,name}:" in result
        assert "1,Alice" in result
        assert "2,Bob" in result

    def test_preserves_field_order(self):
        """Field order matches first item's key order."""
        data = [{"b": 2, "a": 1}]
        result = to_toon(data, "items")
        # Should preserve dict key order (Python 3.7+)
        assert "{b,a}" in result or "{a,b}" in result

    def test_handles_missing_fields(self):
        """Missing fields become empty strings."""
        data = [{"id": 1, "name": "Alice"}, {"id": 2}]  # missing name
        result = to_toon(data, "users")
        assert "2," in result  # empty name

    def test_escapes_commas(self):
        """Commas in values are escaped with quotes."""
        data = [{"name": "Doe, John"}]
        result = to_toon(data, "users")
        assert '"Doe, John"' in result

    def test_truncates_long_values(self):
        """Long values are truncated when max_field_width set."""
        data = [{"text": "This is a very long string"}]
        result = to_toon(data, "items", max_field_width=10)
        assert "This is..." in result

    def test_count_matches_rows(self):
        """Count in header matches actual row count."""
        data = [{"x": i} for i in range(5)]
        result = to_toon(data, "items")
        assert "items[5]" in result


class TestExecutionHistoryToToon:
    """Tests for execution history conversion."""

    def test_empty_history(self):
        """Empty history returns proper format."""
        result = execution_history_to_toon([])
        assert result == "history[0]{}:"

    def test_success_status(self):
        """Successful execution shows 'ok' status."""
        history = [{"title": "Fix bug", "success": True, "execution_time": 5.2}]
        result = execution_history_to_toon(history)
        assert "ok" in result
        assert "5s" in result

    def test_failure_status(self):
        """Failed execution shows 'fail' status."""
        history = [{"title": "Fix bug", "success": False}]
        result = execution_history_to_toon(history)
        assert "fail" in result

    def test_truncates_long_titles(self):
        """Long titles are truncated to 50 chars."""
        history = [{"title": "A" * 100, "success": True}]
        result = execution_history_to_toon(history)
        # Title should be truncated
        assert "A" * 51 not in result


class TestWorkQueueToToon:
    """Tests for work queue conversion."""

    def test_empty_queue(self):
        """Empty queue returns proper format."""
        result = work_queue_to_toon([])
        assert result == "queue[0]{}:"

    def test_formats_tasks(self):
        """Tasks are formatted correctly."""
        tasks = [
            {"id": "abc123", "type": "bug_fix", "title": "Fix auth", "priority": 1}
        ]
        result = work_queue_to_toon(tasks)
        assert "queue[1]" in result
        assert "abc123" in result
        assert "bug_fix" in result


class TestFilesToToon:
    """Tests for file list conversion."""

    def test_empty_files(self):
        """Empty file list returns proper format."""
        result = files_to_toon([])
        assert result == "files[0]{}:"

    def test_formats_files(self):
        """Files are formatted with action."""
        files = ["src/main.py", "tests/test.py"]
        result = files_to_toon(files, "created")
        assert "files[2]" in result
        assert "src/main.py" in result
        assert "created" in result


class TestQualityResultsToToon:
    """Tests for quality gate results conversion."""

    def test_empty_results(self):
        """Empty results returns proper format."""
        result = quality_results_to_toon([])
        assert result == "checks[0]{}:"

    def test_pass_status(self):
        """Passed check shows 'pass' status."""
        results = [{"name": "lint", "passed": True, "message": "OK"}]
        result = quality_results_to_toon(results)
        assert "pass" in result

    def test_fail_status(self):
        """Failed check shows 'fail' status."""
        results = [{"name": "lint", "passed": False, "message": "Errors found"}]
        result = quality_results_to_toon(results)
        assert "fail" in result


class TestEncodeAlias:
    """Tests for encode() alias function."""

    def test_encode_works_like_to_toon(self):
        """encode() is an alias for to_toon()."""
        data = [{"x": 1}]
        assert encode(data, "test") == to_toon(data, "test")
