"""
Default Profile - General-purpose development assistance
"""

from typing import Any, Dict, List, Optional

from .base import BaseProfile, ProfileConfig


class DefaultProfile(BaseProfile):
    """
    Default profile for general-purpose development tasks.

    This profile provides broad capabilities for:
    - Bug fixes
    - Feature implementation
    - Refactoring
    - Documentation
    - Testing
    """

    def __init__(self, config: Optional[ProfileConfig] = None):
        """Initialize the default profile"""
        if config is None:
            config = ProfileConfig(
                name="default",
                description="General-purpose development assistance",
                allowed_tools=[
                    "Read",
                    "Write",
                    "Edit",
                    "Bash",
                    "Glob",
                    "Grep",
                ],
            )
        super().__init__(config)

    def get_system_prompt(self, context: Optional[Dict[str, Any]] = None) -> str:
        """Get the system prompt for general development"""
        base_prompt = """You are Sugar, an autonomous development assistant.

Your goal is to complete development tasks efficiently and correctly.

## Capabilities
- Read, write, and edit files
- Execute shell commands
- Search codebases
- Run tests
- Create and manage git commits

## Guidelines
1. **Understand First**: Read relevant files before making changes
2. **Follow Patterns**: Match existing code style and conventions
3. **Test Changes**: Run tests when available
4. **Document**: Add comments for complex logic
5. **Be Minimal**: Make only the changes needed for the task

## Safety
- Never commit sensitive data (API keys, passwords)
- Don't delete files without explicit instruction
- Preserve existing functionality unless asked to change it
"""

        if context:
            project_name = context.get("project_name", "")
            if project_name:
                base_prompt += f"\n\nProject: {project_name}"

            additional_context = context.get("additional_context", "")
            if additional_context:
                base_prompt += f"\n\nContext:\n{additional_context}"

        return base_prompt

    async def process_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input for general development tasks"""
        # Extract and normalize common fields
        processed = {
            "task_type": input_data.get("type", "general"),
            "title": input_data.get("title", "Development Task"),
            "description": input_data.get("description", ""),
            "priority": input_data.get("priority", 3),
            "context": input_data.get("context", {}),
        }

        # Build the prompt
        prompt = f"""# Task: {processed['title']}

## Type: {processed['task_type']}
## Priority: {processed['priority']}/5

## Description
{processed['description']}

Please complete this task following the guidelines in your system prompt.
"""

        processed["prompt"] = prompt
        return processed

    async def process_output(self, output_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process output from development tasks"""
        # Extract summary and key information
        content = output_data.get("content", "")

        processed = {
            "success": output_data.get("success", True),
            "content": content,
            "summary": self._extract_summary(content),
            "files_modified": output_data.get("files_modified", []),
            "tool_uses": output_data.get("tool_uses", []),
        }

        return processed

    def _extract_summary(self, content: str) -> str:
        """Extract a summary from the content"""
        if not content:
            return ""

        # Take first meaningful line
        lines = content.strip().split("\n")
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#") and len(line) > 10:
                return line[:200]

        return content[:200] if content else ""
