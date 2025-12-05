"""
Tests for the sugar.learning module initialization and import structure.

This module verifies that the learning subsystem components are properly
importable and correctly structured. The learning module provides Sugar's
adaptive capabilities, including feedback processing and task scheduling
optimization.

These smoke tests ensure that:
- The learning package is correctly configured as a Python module
- Core components (FeedbackProcessor, AdaptiveScheduler) are accessible
- Component types are correctly defined as classes

These tests catch import errors, circular dependencies, and module
configuration issues early in the test suite.
"""

import pytest


class TestLearningModuleImports:
    """
    Verify that learning module components are properly importable.

    This test class validates the import structure of the sugar.learning
    package. Import tests serve as smoke tests that run quickly and catch
    fundamental issues like missing dependencies, syntax errors in module
    files, or broken package configurations.

    The learning module contains:
    - FeedbackProcessor: Handles processing and learning from task execution
      feedback to improve future performance
    - AdaptiveScheduler: Optimizes task scheduling based on learned patterns
      and system state
    """

    def test_import_learning_module(self):
        """
        Verify the learning package itself is importable.

        This test ensures the sugar.learning package is properly configured
        with a valid __init__.py and has no top-level import errors.
        """
        import sugar.learning

        assert sugar.learning is not None

    def test_import_feedback_processor(self):
        """
        Verify FeedbackProcessor is importable from its submodule.

        FeedbackProcessor is responsible for collecting and processing
        execution feedback to enable learning from task outcomes.
        """
        from sugar.learning.feedback_processor import FeedbackProcessor

        assert FeedbackProcessor is not None

    def test_import_adaptive_scheduler(self):
        """
        Verify AdaptiveScheduler is importable from its submodule.

        AdaptiveScheduler uses learned patterns to optimize when and how
        tasks are scheduled for execution.
        """
        from sugar.learning.adaptive_scheduler import AdaptiveScheduler

        assert AdaptiveScheduler is not None

    def test_feedback_processor_is_class(self):
        """
        Verify FeedbackProcessor is defined as a class type.

        This ensures the component is properly defined and can be
        instantiated, ruling out accidental exports of instances
        or functions.
        """
        from sugar.learning.feedback_processor import FeedbackProcessor

        assert isinstance(FeedbackProcessor, type)

    def test_adaptive_scheduler_is_class(self):
        """
        Verify AdaptiveScheduler is defined as a class type.

        This ensures the component is properly defined and can be
        instantiated, ruling out accidental exports of instances
        or functions.
        """
        from sugar.learning.adaptive_scheduler import AdaptiveScheduler

        assert isinstance(AdaptiveScheduler, type)
