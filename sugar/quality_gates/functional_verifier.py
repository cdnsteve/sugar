"""
Functional Verification Layer - Feature 2: Functional Verification

Verifies that fixes actually work in the running application through:
- HTTP requests
- Browser automation (via MCP tools)
- Database queries
"""

import asyncio
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import logging
import re

logger = logging.getLogger(__name__)


class FunctionalVerificationResult:
    """Result of a functional verification"""

    def __init__(
        self,
        verification_type: str,
        verified: bool,
        expected: Any,
        actual: Any,
        **kwargs,
    ):
        self.type = verification_type
        self.verified = verified
        self.expected = expected
        self.actual = actual
        self.metadata = kwargs
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        """Convert to dictionary"""
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
    Verifies that fixes actually work in the running application
    """

    def __init__(self, config: dict):
        """
        Initialize functional verifier

        Args:
            config: Configuration dictionary
        """
        verification_config = config.get("quality_gates", {}).get(
            "functional_verification", {}
        )
        self.enabled = verification_config.get("enabled", False)
        self.required = verification_config.get("required", False)
        self.methods_config = verification_config.get("methods", {})
        self.auto_detect = verification_config.get("auto_detect", {})

    def is_enabled(self) -> bool:
        """Check if functional verification is enabled"""
        return self.enabled

    async def verify_all(
        self,
        verifications: List[Dict[str, Any]],
        changed_files: List[str] = None,
    ) -> Tuple[bool, List[FunctionalVerificationResult]]:
        """
        Run all functional verifications

        Args:
            verifications: List of verification definitions
            changed_files: List of changed files for auto-detection

        Returns:
            Tuple of (all_verified, list of results)
        """
        if not self.is_enabled():
            return True, []

        # Auto-detect verifications based on changed files
        if changed_files and self.auto_detect.get("enabled", False):
            auto_verifications = self._auto_detect_verifications(changed_files)
            verifications = verifications + auto_verifications

        if not verifications:
            logger.info("No functional verifications to run")
            return True, []

        results = []
        for verification_def in verifications:
            result = await self._verify_single(verification_def)
            results.append(result)

        all_verified = all(r.verified for r in results)

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
        Verify a single functional requirement

        Args:
            verification_def: Verification definition

        Returns:
            FunctionalVerificationResult
        """
        verification_type = verification_def.get("type")

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
        """Verify HTTP request returns expected result"""
        url = verification_def.get("url")
        method = verification_def.get("method", "GET").upper()
        expected_status = verification_def.get("expected_status", 200)
        timeout = self.methods_config.get("http_requests", {}).get("timeout", 10)

        try:
            # Use curl for HTTP requests
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

            # Add headers if specified
            headers = verification_def.get("headers", {})
            for key, value in headers.items():
                curl_args.extend(["-H", f"{key}: {value}"])

            # Add body if specified (for POST/PUT)
            body = verification_def.get("body")
            if body:
                if isinstance(body, dict):
                    body = json.dumps(body)
                curl_args.extend(["-d", body])

            curl_args.append(url)

            process = await asyncio.create_subprocess_exec(
                *curl_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()
            output = stdout.decode("utf-8").strip()

            # Parse output: status_code|time_total
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
        """Verify HTTP status code (simpler version)"""
        # Delegate to http_request verification
        return await self._verify_http_request(verification_def)

    async def _verify_browser_element(
        self, verification_def: Dict[str, Any]
    ) -> FunctionalVerificationResult:
        """
        Verify browser element exists (requires MCP Chrome DevTools)

        This is a placeholder that checks if MCP tools are available.
        Actual implementation would use Chrome DevTools MCP.
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

        # TODO: Integrate with Chrome DevTools MCP when available
        # For now, return unverified
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
        Take screenshot for verification (requires MCP Chrome DevTools)

        This is a placeholder for future MCP integration.
        """
        url = verification_def.get("url")
        screenshot_path = verification_def.get("screenshot_path")

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
        Verify database query result

        This is a placeholder for database verification.
        Actual implementation would use database-specific tools.
        """
        query = verification_def.get("query")
        expected_result = verification_def.get("expected_result")

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
        """Verify that a port is listening"""
        port = verification_def.get("port")
        host = verification_def.get("host", "localhost")

        try:
            # Use netstat/lsof to check if port is listening
            process = await asyncio.create_subprocess_shell(
                f"lsof -i :{port} -sTCP:LISTEN",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()
            output = stdout.decode("utf-8")

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
        Auto-detect required verifications based on changed files

        Args:
            changed_files: List of file paths that were changed

        Returns:
            List of verification definitions
        """
        verifications = []
        patterns = self.auto_detect.get("patterns", [])

        for file_path in changed_files:
            for pattern_config in patterns:
                pattern = pattern_config.get("pattern", "")
                # Simple glob-style matching
                if self._matches_pattern(file_path, pattern):
                    verification_type = pattern_config.get("verification")
                    test_config = pattern_config.get("test_config", {})

                    if verification_type == "http_requests":
                        # Extract test URLs from config
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
        """Simple glob pattern matching"""
        import fnmatch

        return fnmatch.fnmatch(file_path, pattern)
