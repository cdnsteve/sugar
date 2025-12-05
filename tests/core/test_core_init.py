"""
Tests for sugar/core/__init__.py module exports.

This module tests that the core module correctly exports its public API
and that imports work as expected.
"""

import inspect


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

    def test_sugarloop_is_class(self):
        """Test that SugarLoop is actually a class, not a function or module."""
        from sugar.core import SugarLoop

        assert inspect.isclass(SugarLoop)

    def test_all_exports_are_accessible(self):
        """Test that all items in __all__ are actually accessible via getattr."""
        import sugar.core

        for name in sugar.core.__all__:
            obj = getattr(sugar.core, name, None)
            assert obj is not None, f"{name} is in __all__ but not accessible"

    def test_no_unexpected_public_exports(self):
        """Test that __all__ only contains expected public exports.

        This helps ensure that new exports are intentionally added
        and documented in __all__.
        """
        import sugar.core

        # Only SugarLoop should be exported
        expected_exports = {"SugarLoop"}
        actual_exports = set(sugar.core.__all__)

        assert (
            actual_exports == expected_exports
        ), f"Unexpected exports found: {actual_exports - expected_exports}"

    def test_module_docstring_has_usage_example(self):
        """Test that module docstring includes a usage example."""
        import sugar.core

        docstring = sugar.core.__doc__
        assert "from sugar.core import SugarLoop" in docstring
        assert "await loop" in docstring or "loop." in docstring

    def test_module_docstring_references_submodules(self):
        """Test that module docstring references integration points."""
        import sugar.core

        docstring = sugar.core.__doc__
        # Should reference key integration modules
        assert "discovery" in docstring.lower()
        assert "executor" in docstring.lower()
        assert "storage" in docstring.lower()

    def test_sugarloop_has_expected_methods(self):
        """Test that SugarLoop class has key public methods.

        This is a smoke test to ensure the re-export includes the full class.
        """
        from sugar.core import SugarLoop

        expected_methods = ["start", "stop", "health_check"]
        for method_name in expected_methods:
            assert hasattr(
                SugarLoop, method_name
            ), f"SugarLoop should have {method_name} method"
            method = getattr(SugarLoop, method_name)
            assert callable(method), f"{method_name} should be callable"
