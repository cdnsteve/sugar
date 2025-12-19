"""
Issue Responder Profile - GitHub issue analysis and response

This profile specializes in:
- Analyzing GitHub issues
- Searching codebases for relevant information
- Finding similar issues
- Generating helpful responses
- Applying confidence-based auto-posting
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base import BaseProfile, ProfileConfig

logger = logging.getLogger(__name__)


@dataclass
class IssueAnalysis:
    """Result of analyzing a GitHub issue"""

    issue_number: int
    title: str
    body: str
    issue_type: str  # bug, feature, question, documentation
    sentiment: str  # frustrated, neutral, positive
    key_topics: List[str]
    mentioned_files: List[str]
    mentioned_errors: List[str]
    similar_issues: List[int]
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "issue_number": self.issue_number,
            "title": self.title,
            "body": self.body,
            "issue_type": self.issue_type,
            "sentiment": self.sentiment,
            "key_topics": self.key_topics,
            "mentioned_files": self.mentioned_files,
            "mentioned_errors": self.mentioned_errors,
            "similar_issues": self.similar_issues,
            "confidence": self.confidence,
        }


@dataclass
class IssueResponse:
    """Generated response for an issue"""

    content: str
    confidence: float
    code_references: List[Dict[str, Any]]
    suggested_labels: List[str]
    should_auto_post: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "confidence": self.confidence,
            "code_references": self.code_references,
            "suggested_labels": self.suggested_labels,
            "should_auto_post": self.should_auto_post,
        }


class IssueResponderProfile(BaseProfile):
    """
    Profile for responding to GitHub issues.

    Features:
    - Issue classification (bug, feature, question)
    - Codebase search for relevant context
    - Similar issue detection
    - Response generation with code references
    - Confidence-based auto-posting
    """

    def __init__(self, config: Optional[ProfileConfig] = None):
        """Initialize the issue responder profile"""
        if config is None:
            config = ProfileConfig(
                name="issue_responder",
                description="GitHub issue analysis and response",
                allowed_tools=[
                    "Read",
                    "Glob",
                    "Grep",
                ],
                settings={
                    "auto_post_threshold": 0.8,
                    "max_response_length": 2000,
                    "include_signature": True,
                    "signature": "\n\n---\n*Sugar (AI Assistant) • [Learn more](https://github.com/roboticforce/sugar)*",
                },
            )
        super().__init__(config)

    def get_system_prompt(self, context: Optional[Dict[str, Any]] = None) -> str:
        """Get the system prompt for issue response"""
        repo_info = ""
        if context:
            repo = context.get("repo", "")
            if repo:
                repo_info = f"\nRepository: {repo}"

        return f"""You are Sugar, an AI assistant that helps respond to GitHub issues.

{repo_info}

## Your Role
You analyze GitHub issues and provide helpful, accurate responses based on:
1. The issue content and context
2. The codebase structure and implementation
3. Similar previously resolved issues
4. Documentation and README files

## Response Guidelines

### Do:
- Be helpful and welcoming to the issue author
- Reference specific files and line numbers when relevant
- Provide code examples when helpful
- Suggest related documentation
- Be concise but thorough

### Don't:
- Claim to be a maintainer or have merge permissions
- Make promises about when issues will be fixed
- Dismiss user concerns without investigation
- Post responses with low confidence
- Include sensitive information

## Response Format

Structure your responses like this:
1. **Acknowledgment** - Thank them and show you understand the issue
2. **Analysis** - What you found in the codebase
3. **Solution/Guidance** - Specific help or next steps
4. **References** - Links to relevant code or docs

## Confidence Scoring

Rate your confidence in your response:
- **0.9-1.0**: Very confident, verified in code
- **0.7-0.9**: Confident, based on patterns and context
- **0.5-0.7**: Moderate, some uncertainty
- **0.0-0.5**: Low, needs human review

Only auto-post responses with confidence >= 0.8.
"""

    async def process_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process issue data for analysis"""
        issue = input_data.get("issue", {})

        # Extract issue details
        issue_number = issue.get("number", 0)
        title = issue.get("title", "")
        body = issue.get("body", "")
        raw_labels = issue.get("labels", [])
        # Handle labels as either strings or dicts with 'name' key
        labels = [
            l.get("name", str(l)) if isinstance(l, dict) else str(l)
            for l in raw_labels
        ]
        author = issue.get("user", {}).get("login", "unknown")

        # Pre-analyze the issue
        analysis = self._pre_analyze_issue(title, body, labels)

        # Build the prompt
        prompt = f"""# Analyze and Respond to Issue #{issue_number}

## Issue Details
- **Title**: {title}
- **Author**: {author}
- **Labels**: {', '.join(labels) if labels else 'None'}

## Issue Body
{body}

## Pre-Analysis
- **Detected Type**: {analysis['issue_type']}
- **Key Topics**: {', '.join(analysis['key_topics'])}
- **Mentioned Files**: {', '.join(analysis['mentioned_files']) or 'None detected'}
- **Error Patterns**: {', '.join(analysis['mentioned_errors']) or 'None detected'}

## Your Task

1. **Search the codebase** for relevant files and context
2. **Analyze** how the issue relates to the implementation
3. **Generate a response** that helps the issue author
4. **Rate your confidence** in the response

Provide your response in this format:

### Confidence Score
[0.0-1.0]

### Suggested Labels
[comma-separated list]

### Response
[Your response to post on the issue]

### Code References
[List of file:line references used]
"""

        return {
            "prompt": prompt,
            "issue_number": issue_number,
            "issue_title": title,
            "issue_body": body,
            "pre_analysis": analysis,
            "repo": input_data.get("repo", ""),
        }

    async def process_output(self, output_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process agent output into structured response"""
        content = output_data.get("content", "")

        # Parse the structured response
        parsed = self._parse_response(content)

        # Build the response
        response_content = parsed.get("response", content)

        # Add signature if configured
        if self.config.settings.get("include_signature", True):
            signature = self.config.settings.get("signature", "")
            if signature and signature not in response_content:
                response_content += signature

        # Truncate if needed
        max_length = self.config.settings.get("max_response_length", 2000)
        if len(response_content) > max_length:
            response_content = response_content[:max_length - 3] + "..."

        confidence = parsed.get("confidence", 0.5)
        auto_post_threshold = self.config.settings.get("auto_post_threshold", 0.8)

        return {
            "success": True,
            "response": IssueResponse(
                content=response_content,
                confidence=confidence,
                code_references=parsed.get("code_references", []),
                suggested_labels=parsed.get("suggested_labels", []),
                should_auto_post=confidence >= auto_post_threshold,
            ).to_dict(),
            "raw_output": content,
        }

    def _pre_analyze_issue(
        self, title: str, body: str, labels: List[str]
    ) -> Dict[str, Any]:
        """Pre-analyze issue to extract key information"""
        text = f"{title} {body}".lower()

        # Detect issue type
        issue_type = "question"
        if any(word in text for word in ["bug", "error", "crash", "fail", "broken"]):
            issue_type = "bug"
        elif any(word in text for word in ["feature", "request", "would be nice", "add support"]):
            issue_type = "feature"
        elif any(word in text for word in ["docs", "documentation", "readme", "example"]):
            issue_type = "documentation"

        # Extract file mentions
        file_pattern = r'[\w/.-]+\.(py|js|ts|go|rs|java|md|yaml|json|tsx|jsx)'
        mentioned_files = list(set(re.findall(file_pattern, f"{title} {body}")))

        # Extract error patterns
        error_patterns = [
            r'error:?\s*["\']?([^"\']+)["\']?',
            r'exception:?\s*([^\n]+)',
            r'traceback[^\n]*\n([^\n]+)',
        ]
        mentioned_errors = []
        for pattern in error_patterns:
            matches = re.findall(pattern, body, re.IGNORECASE)
            mentioned_errors.extend(matches[:3])  # Limit to 3

        # Extract key topics (simple keyword extraction)
        key_topics = []
        topic_keywords = [
            "api", "auth", "database", "config", "install", "import",
            "test", "build", "deploy", "docker", "cli", "hook",
            "mcp", "agent", "sdk", "permission", "timeout",
        ]
        for keyword in topic_keywords:
            if keyword in text:
                key_topics.append(keyword)

        return {
            "issue_type": issue_type,
            "key_topics": key_topics[:5],
            "mentioned_files": mentioned_files[:5],
            "mentioned_errors": mentioned_errors[:3],
        }

    def _parse_response(self, content: str) -> Dict[str, Any]:
        """Parse the structured agent response"""
        result = {
            "confidence": 0.5,
            "suggested_labels": [],
            "response": content,
            "code_references": [],
        }

        # Extract confidence score
        confidence_match = re.search(
            r'confidence\s*(?:score)?[:\s]*([0-9.]+)',
            content,
            re.IGNORECASE
        )
        if confidence_match:
            try:
                result["confidence"] = float(confidence_match.group(1))
            except ValueError:
                pass

        # Extract suggested labels
        labels_match = re.search(
            r'suggested\s*labels[:\s]*([^\n]+)',
            content,
            re.IGNORECASE
        )
        if labels_match:
            labels_text = labels_match.group(1)
            result["suggested_labels"] = [
                l.strip() for l in labels_text.split(",")
                if l.strip() and l.strip() not in ["None", "none", "-"]
            ]

        # Extract the actual response section
        response_match = re.search(
            r'###\s*Response\s*\n(.*?)(?=###|$)',
            content,
            re.DOTALL | re.IGNORECASE
        )
        if response_match:
            result["response"] = response_match.group(1).strip()

        # Extract code references
        refs_match = re.search(
            r'###\s*Code\s*References\s*\n(.*?)(?=###|$)',
            content,
            re.DOTALL | re.IGNORECASE
        )
        if refs_match:
            refs_text = refs_match.group(1)
            ref_pattern = r'([^\s:]+):(\d+)'
            for match in re.finditer(ref_pattern, refs_text):
                result["code_references"].append({
                    "file": match.group(1),
                    "line": int(match.group(2)),
                })

        return result

    def validate_output(self, output: Dict[str, Any]) -> bool:
        """Validate issue response meets requirements"""
        response = output.get("response", {})
        if isinstance(response, dict):
            content = response.get("content", "")
            confidence = response.get("confidence", 0)
        else:
            content = str(response)
            confidence = 0.5

        # Check minimum content length
        if len(content) < 50:
            logger.warning("Response too short")
            return False

        # Check confidence threshold
        if confidence < self.config.confidence_threshold:
            logger.warning(f"Confidence {confidence} below threshold {self.config.confidence_threshold}")
            return False

        return True
