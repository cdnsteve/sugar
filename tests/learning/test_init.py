"""
Tests for the sugar.learning module initialization.
"""

import pytest


class TestLearningModuleImports:
    """Tests for module imports."""

    def test_import_learning_module(self):
        """Test that the learning module can be imported."""
        import sugar.learning

        assert sugar.learning is not None

    def test_import_feedback_processor(self):
        """Test that FeedbackProcessor can be imported from submodule."""
        from sugar.learning.feedback_processor import FeedbackProcessor

        assert FeedbackProcessor is not None

    def test_import_adaptive_scheduler(self):
        """Test that AdaptiveScheduler can be imported from submodule."""
        from sugar.learning.adaptive_scheduler import AdaptiveScheduler

        assert AdaptiveScheduler is not None

    def test_feedback_processor_is_class(self):
        """Test that FeedbackProcessor is a class."""
        from sugar.learning.feedback_processor import FeedbackProcessor

        assert isinstance(FeedbackProcessor, type)

    def test_adaptive_scheduler_is_class(self):
        """Test that AdaptiveScheduler is a class."""
        from sugar.learning.adaptive_scheduler import AdaptiveScheduler

        assert isinstance(AdaptiveScheduler, type)
