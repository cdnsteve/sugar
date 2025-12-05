"""
Functional Verification Layer - Feature 2: Functional Verification

This module provides runtime verification of code changes by testing that fixes
actually work in a running application environment. It bridges the gap between
static testing (unit tests, type checks) and real-world behavior.

Supported Verification Types:
    - HTTP requests: Verify API endpoints respond correctly
    - HTTP status codes: Simplified status code verification
    - Browser elements: Check DOM elements exist (requires MCP Chrome DevTools)
    - Browser screenshots: Capture page state for visual verification
    - Database queries: Verify data state after changes
    - Port listening: Confirm services are running on expected ports

Integration Points:
    - Uses curl for HTTP verification (no external Python dependencies)
    - Uses lsof for port checking on Unix-like systems
    - Browser automation via MCP Chrome DevTools (placeholder - not yet integrated)

Configuration:
    Enabled via the config dictionary under:
    config["quality_gates"]["functional_verification"]

    Key settings:
        - enabled: bool - Whether functional verification is active
        - required: bool - Whether verification failures block progress
        - methods: dict - Method-specific configuration (timeouts, etc.)
        - auto_detect: dict - Automatic verification detection settings

Example Usage:
    >>> config = {"quality_gates": {"functional_verification": {"enabled": True}}}
    >>> verifier = FunctionalVerifier(config)
    >>> verifications = [{"type": "http_request", "url": "http://localhost:8000/health"}]
    >>> success, results = await verifier.verify_all(verifications)
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


class FunctionalVerificationResult:
    """
    Result container for a single functional verification.

    This class captures the outcome of a verification check, including whether
    it passed, what was expected vs actual, and any additional metadata specific
    to the verification type.

    Attributes:
        type: The verification type (e.g., "http_request", "port_listening")
        verified: Whether the verification passed (True) or failed (False)
        expected: The expected value or condition
        actual: The actual observed value or condition
        metadata: Additional key-value pairs specific to the verification type
            (e.g., url, method, response_time for HTTP verifications)
        timestamp: ISO format timestamp when the verification was performed

    Example:
        >>> result = FunctionalVerificationResult(
        ...     verification_type="http_request",
        ...     verified=True,
        ...     expected=200,
        ...     actual=200,
        ...     url="http://localhost:8000/health",
        ...     response_time_seconds=0.05
        ... )
        >>> result.verified
        True
        >>> result.to_dict()["url"]
        'http://localhost:8000/health'
    """

    def __init__(
        self,
        verification_type: str,
        verified: bool,
        expected: Any,
        actual: Any,
        **kwargs,
    ):
        """
        Initialize a verification result.

        Args:
            verification_type: String identifier for the type of verification
                (e.g., "http_request", "port_listening", "browser_element")
            verified: Boolean indicating if verification passed
            expected: The expected value, condition, or state being verified
            actual: The actual observed value, condition, or state
            **kwargs: Additional metadata fields that will be included in
                serialization (e.g., url, error, note, response_time_seconds)
        """
        self.type = verification_type
        self.verified = verified
        self.expected = expected
        self.actual = actual
        self.metadata = kwargs
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> dict:
        """
        Convert the result to a dictionary for serialization.

        Returns:
            Dictionary containing all result fields including metadata.
            Structure: {type, verified, expected, actual, timestamp, ...metadata}
        """
        return {
            "type": self.type,
            "verified": self.verified,
            "expected": self.expected,
            "actual": self.actual,
            "timestamp": self.timestamp,
            **self.metadata,
        }


class FunctionalVerifier:
    """
    Verifies that code changes work correctly in a running application.

    This class orchestrates functional verification by routing verification
    definitions to appropriate handlers based on type. It supports HTTP
    verification, port checking, and placeholder implementations for browser
    automation and database queries.

    Attributes:
        enabled: Whether functional verification is active
        required: Whether verification failures should block progress
        methods_config: Configuration for specific verification methods
            (e.g., HTTP timeout settings)
        auto_detect: Configuration for automatic verification detection
            based on changed files

    Configuration Structure:
        The config dict should contain::

            {
                "quality_gates": {
                    "functional_verification": {
                        "enabled": true,
                        "required": false,
                        "methods": {
                            "http_requests": {"timeout": 10}
                        },
                        "auto_detect": {
                            "enabled": true,
                            "patterns": [...]
                        }
                    }
                }
            }
    """

    def __init__(self, config: dict):
        """
        Initialize the functional verifier with configuration.

        Args:
            config: Full application configuration dictionary. The verifier
                extracts its settings from config["quality_gates"]["functional_verification"].
                Missing keys default to safe values (disabled, not required).
        """
        verification_config = config.get("quality_gates", {}).get(
            "functional_verification", {}
        )
        self.enabled = verification_config.get("enabled", False)
        self.required = verification_config.get("required", False)
        self.methods_config = verification_config.get("methods", {})
        self.auto_detect = verification_config.get("auto_detect", {})

    def is_enabled(self) -> bool:
        """
        Check if functional verification is enabled.

        Returns:
            True if functional verification is active, False otherwise.
        """
        return self.enabled

    async def verify_all(
        self,
        verifications: List[Dict[str, Any]],
        changed_files: List[str] = None,
    ) -> Tuple[bool, List[FunctionalVerificationResult]]:
        """
        Run all functional verifications and collect results.

        This is the main entry point for verification. It processes all provided
        verification definitions, optionally auto-detects additional verifications
        based on changed files, and returns aggregated results.

        Args:
            verifications: List of verification definition dictionaries. Each dict
                must contain a "type" key indicating the verification type.
                Additional keys depend on type:
                - http_request: url, method, expected_status, headers, body
                - browser_element: url, selector, mcp_tools_available
                - database_query: query, expected_result
                - port_listening: port, host
            changed_files: Optional list of file paths that changed. When provided
                and auto_detect is enabled, additional verifications may be added
                based on configured patterns.

        Returns:
            Tuple containing:
                - bool: True if all verifications passed, False if any failed
                - List[FunctionalVerificationResult]: Individual results for each
                  verification, preserving order

        Note:
            Returns (True, []) if verification is disabled or no verifications
            are defined. This allows callers to proceed without special handling.
        """
        if not self.is_enabled():
            return True, []

        # Auto-detect additional verifications based on changed files if enabled
        if changed_files and self.auto_detect.get("enabled", False):
            auto_verifications = self._auto_detect_verifications(changed_files)
            verifications = verifications + auto_verifications

        if not verifications:
            logger.info("No functional verifications to run")
            return True, []

        # Execute each verification sequentially and collect results
        results = []
        for verification_def in verifications:
            result = await self._verify_single(verification_def)
            results.append(result)

        # Determine overall success (all must pass)
        all_verified = all(r.verified for r in results)

        # Log summary with appropriate level based on outcome
        if all_verified:
            logger.info(f"✅ All {len(results)} functional verifications passed")
        else:
            failed = [r for r in results if not r.verified]
            logger.warning(
                f"❌ {len(failed)} functional verifications failed: {[r.type for r in failed]}"
            )

        return all_verified, results

    async def _verify_single(
        self, verification_def: Dict[str, Any]
    ) -> FunctionalVerificationResult:
        """
        Route a single verification to its appropriate handler.

        This method acts as a dispatcher, examining the verification type
        and delegating to the appropriate specialized verification method.

        Args:
            verification_def: Dictionary containing verification parameters.
                Must include a "type" key with one of the supported types:
                - "http_request": Full HTTP request verification
                - "http_status_code": Simplified status code check
                - "browser_element": DOM element existence check (MCP required)
                - "browser_screenshot": Page screenshot capture (MCP required)
                - "database_query": Database state verification (placeholder)
                - "port_listening": Service port availability check

        Returns:
            FunctionalVerificationResult with verification outcome. For
            unsupported types, returns a failed result with an error message.
        """
        verification_type = verification_def.get("type")

        # Route to appropriate handler based on verification type
        if verification_type == "http_request":
            return await self._verify_http_request(verification_def)
        elif verification_type == "http_status_code":
            return await self._verify_http_status_code(verification_def)
        elif verification_type == "browser_element":
            return await self._verify_browser_element(verification_def)
        elif verification_type == "browser_screenshot":
            return await self._verify_browser_screenshot(verification_def)
        elif verification_type == "database_query":
            return await self._verify_database_query(verification_def)
        elif verification_type == "port_listening":
            return await self._verify_port_listening(verification_def)
        else:
            # Unknown verification type - log and return failure
            logger.error(f"Unknown verification type: {verification_type}")
            return FunctionalVerificationResult(
                verification_type=verification_type,
                verified=False,
                expected=verification_def.get("expected"),
                actual=None,
                error=f"Unsupported verification type: {verification_type}",
            )

    async def _verify_http_request(
        self, verification_def: Dict[str, Any]
    ) -> FunctionalVerificationResult:
        """
        Verify an HTTP endpoint responds with the expected status code.

        Uses curl subprocess for HTTP requests to avoid external Python
        dependencies. Captures both status code and response time.

        Args:
            verification_def: Dictionary with HTTP verification parameters:
                - url (str, required): Target URL to request
                - method (str, optional): HTTP method, defaults to "GET"
                - expected_status (int, optional): Expected HTTP status, defaults to 200
                - headers (dict, optional): Request headers as key-value pairs
                - body (str|dict, optional): Request body (dict auto-converted to JSON)

        Returns:
            FunctionalVerificationResult with verified=True if status matches expected,
            includes response_time_seconds in metadata on success.

        Raises:
            Does not raise - exceptions are caught and returned as failed results
            with error details in metadata.
        """
        url = verification_def.get("url")
        method = verification_def.get("method", "GET").upper()
        expected_status = verification_def.get("expected_status", 200)
        timeout = self.methods_config.get("http_requests", {}).get("timeout", 10)

        try:
            # Build curl command with options for silent operation and timing output
            # -s: Silent mode (no progress)
            # -o /dev/null: Discard response body
            # -w: Write out format string for status and timing
            curl_args = [
                "curl",
                "-s",
                "-o",
                "/dev/null",
                "-w",
                "%{http_code}|%{time_total}",
                "-X",
                method,
                "--max-time",
                str(timeout),
            ]

            # Add custom headers if provided
            headers = verification_def.get("headers", {})
            for key, value in headers.items():
                curl_args.extend(["-H", f"{key}: {value}"])

            # Add request body for methods that support it (POST, PUT, PATCH)
            body = verification_def.get("body")
            if body:
                if isinstance(body, dict):
                    body = json.dumps(body)
                curl_args.extend(["-d", body])

            curl_args.append(url)

            # Execute curl asynchronously
            process = await asyncio.create_subprocess_exec(
                *curl_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()
            output = stdout.decode("utf-8").strip()

            # Parse curl output format: "status_code|response_time"
            parts = output.split("|")
            if len(parts) == 2:
                status_code = int(parts[0])
                response_time = float(parts[1])

                verified = status_code == expected_status

                return FunctionalVerificationResult(
                    verification_type="http_request",
                    verified=verified,
                    expected=expected_status,
                    actual=status_code,
                    url=url,
                    method=method,
                    response_time_seconds=response_time,
                )
            else:
                raise Exception(f"Unexpected curl output format: {output}")

        except Exception as e:
            logger.error(f"Error verifying HTTP request to {url}: {e}")
            return FunctionalVerificationResult(
                verification_type="http_request",
                verified=False,
                expected=expected_status,
                actual=None,
                url=url,
                method=method,
                error=str(e),
            )

    async def _verify_http_status_code(
        self, verification_def: Dict[str, Any]
    ) -> FunctionalVerificationResult:
        """
        Verify HTTP status code (simplified alias for http_request).

        This is a convenience type that delegates to _verify_http_request.
        It exists for semantic clarity when only status code verification
        is needed, not full request/response inspection.

        Args:
            verification_def: Same parameters as http_request verification.

        Returns:
            FunctionalVerificationResult from http_request verification.
        """
        return await self._verify_http_request(verification_def)

    async def _verify_browser_element(
        self, verification_def: Dict[str, Any]
    ) -> FunctionalVerificationResult:
        """
        Verify a DOM element exists on a web page.

        This method is a placeholder for browser automation verification.
        Full implementation requires MCP Chrome DevTools integration which
        would allow real browser interaction and DOM inspection.

        Args:
            verification_def: Dictionary with browser element parameters:
                - url (str): Page URL to load
                - selector (str): CSS selector for the target element
                - mcp_tools_available (bool): Whether MCP tools are accessible

        Returns:
            FunctionalVerificationResult with verified=False and a note
            explaining the MCP dependency. When MCP integration is complete,
            this will return verified=True if the element exists.

        Note:
            This is a planned feature. Current implementation always returns
            failed verification with explanatory notes.
        """
        url = verification_def.get("url")
        selector = verification_def.get("selector")
        mcp_available = verification_def.get("mcp_tools_available", False)

        if not mcp_available:
            return FunctionalVerificationResult(
                verification_type="browser_element",
                verified=False,
                expected=f"element exists: {selector}",
                actual=None,
                url=url,
                selector=selector,
                note="Browser automation requires MCP Chrome DevTools - not yet integrated",
            )

        # Placeholder for future MCP Chrome DevTools integration
        # When implemented, this would:
        # 1. Navigate to the URL using MCP browser control
        # 2. Query for the element using the CSS selector
        # 3. Return verified=True if element found, False otherwise
        return FunctionalVerificationResult(
            verification_type="browser_element",
            verified=False,
            expected=f"element exists: {selector}",
            actual=None,
            url=url,
            selector=selector,
            note="MCP integration pending",
        )

    async def _verify_browser_screenshot(
        self, verification_def: Dict[str, Any]
    ) -> FunctionalVerificationResult:
        """
        Capture a screenshot of a web page for visual verification.

        This method is a placeholder for browser screenshot capture.
        Full implementation requires MCP Chrome DevTools integration.
        Screenshots can be used for visual regression testing or manual
        verification of UI changes.

        Args:
            verification_def: Dictionary with screenshot parameters:
                - url (str): Page URL to capture
                - screenshot_path (str): File path to save the screenshot

        Returns:
            FunctionalVerificationResult with verified=False and a note
            explaining the MCP dependency. When implemented, this will
            save a screenshot and return verified=True on success.

        Note:
            This is a planned feature. Current implementation always returns
            failed verification with explanatory notes.
        """
        url = verification_def.get("url")
        screenshot_path = verification_def.get("screenshot_path")

        # Placeholder for future MCP Chrome DevTools integration
        # When implemented, this would:
        # 1. Navigate to the URL using MCP browser control
        # 2. Capture a screenshot of the page
        # 3. Save to screenshot_path
        # 4. Return verified=True on success
        return FunctionalVerificationResult(
            verification_type="browser_screenshot",
            verified=False,
            expected=f"screenshot saved to {screenshot_path}",
            actual=None,
            url=url,
            screenshot_path=screenshot_path,
            note="Screenshot capture requires MCP Chrome DevTools - not yet integrated",
        )

    async def _verify_database_query(
        self, verification_def: Dict[str, Any]
    ) -> FunctionalVerificationResult:
        """
        Verify database state by executing a query and checking the result.

        This method is a placeholder for database verification. Full
        implementation would require database connection configuration
        and support for various database types (PostgreSQL, MySQL, SQLite, etc.).

        Args:
            verification_def: Dictionary with database query parameters:
                - query (str): SQL query to execute
                - expected_result: Expected query result for comparison
                - connection_string (str, optional): Database connection details

        Returns:
            FunctionalVerificationResult with verified=False and a note
            explaining that database verification is not yet implemented.
            When implemented, this will compare actual query results against
            expected_result.

        Note:
            This is a planned feature. Implementation considerations:
            - Support multiple database types via connection strings
            - Handle result comparison for different data types
            - Consider security implications of query execution
        """
        query = verification_def.get("query")
        expected_result = verification_def.get("expected_result")

        # Placeholder for future database verification
        # When implemented, this would:
        # 1. Parse connection string or use configured database
        # 2. Execute the query safely
        # 3. Compare result against expected_result
        # 4. Return verified=True if they match
        return FunctionalVerificationResult(
            verification_type="database_query",
            verified=False,
            expected=expected_result,
            actual=None,
            query=query,
            note="Database query verification not yet implemented",
        )

    async def _verify_port_listening(
        self, verification_def: Dict[str, Any]
    ) -> FunctionalVerificationResult:
        """
        Verify that a service is listening on a specific port.

        Uses lsof to check if any process is listening on the specified port.
        This is useful for verifying that services started successfully after
        code changes.

        Args:
            verification_def: Dictionary with port check parameters:
                - port (int): Port number to check
                - host (str, optional): Host to check, defaults to "localhost"
                    Note: Current implementation only checks local ports.

        Returns:
            FunctionalVerificationResult with verified=True if a process
            is listening on the port, False otherwise.

        Note:
            Uses Unix lsof command. May not work on Windows systems.
            The host parameter is included for future cross-host checking
            but current implementation only checks local ports.
        """
        port = verification_def.get("port")
        host = verification_def.get("host", "localhost")

        try:
            # Use lsof to check for TCP listeners on the specified port
            # -i: Select internet connections
            # :{port}: Filter by port number
            # -sTCP:LISTEN: Only show listening sockets
            process = await asyncio.create_subprocess_shell(
                f"lsof -i :{port} -sTCP:LISTEN",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()
            output = stdout.decode("utf-8")

            # Non-empty output means something is listening
            listening = len(output.strip()) > 0

            return FunctionalVerificationResult(
                verification_type="port_listening",
                verified=listening,
                expected=f"port {port} listening",
                actual=f"port {port} {'listening' if listening else 'not listening'}",
                port=port,
                host=host,
            )

        except Exception as e:
            logger.error(f"Error checking port {port}: {e}")
            return FunctionalVerificationResult(
                verification_type="port_listening",
                verified=False,
                expected=f"port {port} listening",
                actual=None,
                port=port,
                host=host,
                error=str(e),
            )

    def _auto_detect_verifications(
        self, changed_files: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Auto-detect required verifications based on changed file patterns.

        This method examines changed files and generates verification definitions
        based on configured patterns. For example, changes to API route files
        might trigger HTTP endpoint verification.

        Args:
            changed_files: List of file paths that were changed. Paths are
                matched against glob patterns from auto_detect configuration.

        Returns:
            List of verification definition dictionaries ready for execution.
            Empty list if no patterns match or auto_detect is not configured.

        Configuration Format:
            The auto_detect.patterns config should be a list of::

                {
                    "pattern": "*.py",  # Glob pattern to match files
                    "verification": "http_requests",  # Verification type
                    "test_urls": ["http://localhost:8000/api"],
                    "expected_status": [200]
                }

        Note:
            Currently only supports "http_requests" verification type for
            auto-detection. Other types would require additional implementation.
        """
        verifications = []
        patterns = self.auto_detect.get("patterns", [])

        for file_path in changed_files:
            for pattern_config in patterns:
                pattern = pattern_config.get("pattern", "")
                # Use glob-style pattern matching against file path
                if self._matches_pattern(file_path, pattern):
                    verification_type = pattern_config.get("verification")
                    test_config = pattern_config.get("test_config", {})

                    if verification_type == "http_requests":
                        # Generate HTTP verification for each configured test URL
                        test_urls = pattern_config.get("test_urls", [])
                        expected_status = pattern_config.get("expected_status", [200])

                        for url in test_urls:
                            verifications.append(
                                {
                                    "type": "http_request",
                                    "url": url,
                                    "expected_status": (
                                        expected_status[0]
                                        if isinstance(expected_status, list)
                                        else expected_status
                                    ),
                                }
                            )

        if verifications:
            logger.info(
                f"Auto-detected {len(verifications)} verifications from {len(changed_files)} changed files"
            )

        return verifications

    def _matches_pattern(self, file_path: str, pattern: str) -> bool:
        """
        Check if a file path matches a glob pattern.

        Uses Python's fnmatch for Unix shell-style wildcard matching.
        Supports *, ?, and [seq] patterns.

        Args:
            file_path: Full or relative path to match against pattern.
            pattern: Glob pattern (e.g., "*.py", "api/**/*.js", "routes/*")

        Returns:
            True if file_path matches the pattern, False otherwise.

        Examples:
            >>> verifier._matches_pattern("src/api/routes.py", "*.py")
            True
            >>> verifier._matches_pattern("src/api/routes.py", "api/*.py")
            False  # fnmatch doesn't handle directory separators specially
            >>> verifier._matches_pattern("routes.py", "*.py")
            True
        """
        import fnmatch

        return fnmatch.fnmatch(file_path, pattern)
