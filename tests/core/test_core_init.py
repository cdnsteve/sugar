"""
Tests for sugar/core/__init__.py module exports.

This module tests that the core module correctly exports its public API
and that imports work as expected.
"""


class TestCoreModuleExports:
    """Test the sugar.core module's public API exports."""

    def test_sugarloop_exported(self):
        """Test that SugarLoop is exported from sugar.core."""
        from sugar.core import SugarLoop

        assert SugarLoop is not None
        assert hasattr(SugarLoop, "__init__")

    def test_sugarloop_import_equivalence(self):
        """Test that both import paths resolve to the same class."""
        from sugar.core import SugarLoop as SugarLoopFromCore
        from sugar.core.loop import SugarLoop as SugarLoopFromLoop

        assert SugarLoopFromCore is SugarLoopFromLoop

    def test_all_exports(self):
        """Test that __all__ is properly defined."""
        import sugar.core

        assert hasattr(sugar.core, "__all__")
        assert "SugarLoop" in sugar.core.__all__

    def test_module_docstring(self):
        """Test that the module has proper documentation."""
        import sugar.core

        assert sugar.core.__doc__ is not None
        assert "SugarLoop" in sugar.core.__doc__
        assert "orchestration" in sugar.core.__doc__.lower()
