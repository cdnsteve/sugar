#!/usr/bin/env python3
"""
Sugar GitHub Action Entrypoint

Handles the GitHub Actions event and runs the Sugar issue responder.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# Add sugar to path if needed
sys.path.insert(0, "/app")

from sugar.agent import SugarAgent, SugarAgentConfig
from sugar.profiles import IssueResponderProfile, ProfileConfig
from sugar.integrations import GitHubClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("sugar-action")


def get_env(name: str, default: str = "") -> str:
    """Get environment variable with default"""
    return os.environ.get(name, default)


def get_event() -> dict:
    """Load the GitHub event payload"""
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path or not Path(event_path).exists():
        logger.error("No GitHub event found")
        sys.exit(1)

    with open(event_path) as f:
        return json.load(f)


def should_skip_issue(issue: dict, skip_labels: list) -> tuple[bool, str]:
    """Determine if we should skip this issue"""
    # Skip if closed
    if issue.get("state") == "closed":
        return True, "Issue is closed"

    # Skip if PR
    if "pull_request" in issue:
        return True, "This is a pull request, not an issue"

    # Skip if bot author
    author = issue.get("user", {})
    if author.get("type") == "Bot" or author.get("login", "").endswith("[bot]"):
        return True, "Issue created by a bot"

    # Skip if has skip labels
    issue_labels = [l.get("name", "") for l in issue.get("labels", [])]
    for skip_label in skip_labels:
        if skip_label in issue_labels:
            return True, f"Issue has skip label: {skip_label}"

    return False, ""


def set_output(name: str, value: str) -> None:
    """Set a GitHub Actions output"""
    output_file = os.environ.get("GITHUB_OUTPUT")
    if output_file:
        with open(output_file, "a") as f:
            # Handle multiline values
            if "\n" in value:
                delimiter = "EOF"
                f.write(f"{name}<<{delimiter}\n{value}\n{delimiter}\n")
            else:
                f.write(f"{name}={value}\n")


async def run_issue_responder(issue: dict, repo: str) -> dict:
    """Run the issue responder on an issue"""
    # Configuration from environment
    model = get_env("SUGAR_MODEL", "claude-sonnet-4-5")
    confidence_threshold = float(get_env("SUGAR_CONFIDENCE_THRESHOLD", "0.7"))
    max_response_length = int(get_env("SUGAR_MAX_RESPONSE_LENGTH", "2000"))
    dry_run = get_env("SUGAR_DRY_RUN", "false").lower() == "true"

    # Create profile
    profile_config = ProfileConfig(
        name="issue_responder",
        description="GitHub issue responder",
        model=model,
        confidence_threshold=confidence_threshold,
        settings={
            "max_response_length": max_response_length,
            "auto_post_threshold": confidence_threshold,
        },
    )
    profile = IssueResponderProfile(profile_config)

    # Create agent config
    agent_config = SugarAgentConfig(
        model=model,
        permission_mode="acceptEdits",
        quality_gates_enabled=True,
    )

    # Create agent
    agent = SugarAgent(
        config=agent_config,
        quality_gates_config={"enabled": True},
    )

    try:
        # Process input
        input_data = {"issue": issue, "repo": repo}
        processed_input = await profile.process_input(input_data)

        # Run agent
        context = f"Repository: {repo}"
        response = await agent.execute(
            prompt=processed_input["prompt"],
            task_context=context,
        )

        # Process output
        result = await profile.process_output({
            "content": response.content,
            "success": response.success,
        })

        return result

    finally:
        await agent.end_session()


async def main():
    """Main entry point"""
    logger.info("Sugar Issue Responder starting...")

    # Get configuration
    mode = get_env("SUGAR_MODE", "auto")
    skip_labels = [l.strip() for l in get_env("SUGAR_SKIP_LABELS", "").split(",") if l.strip()]
    dry_run = get_env("SUGAR_DRY_RUN", "false").lower() == "true"

    # Load event
    event = get_event()
    action = event.get("action", "")

    logger.info(f"Event action: {action}")
    logger.info(f"Mode: {mode}")
    logger.info(f"Dry run: {dry_run}")

    # Get issue from event
    issue = event.get("issue")
    if not issue:
        logger.info("No issue in event, skipping")
        set_output("responded", "false")
        return

    issue_number = issue.get("number")
    logger.info(f"Processing issue #{issue_number}: {issue.get('title')}")

    # Check if we should skip
    should_skip, skip_reason = should_skip_issue(issue, skip_labels)
    if should_skip:
        logger.info(f"Skipping issue: {skip_reason}")
        set_output("responded", "false")
        return

    # Check mode
    if mode == "mention":
        # Only respond if @sugar is mentioned
        body = issue.get("body", "") or ""
        if "@sugar" not in body.lower():
            logger.info("Mode is 'mention' but @sugar not found, skipping")
            set_output("responded", "false")
            return

    # Get repo info
    repo = event.get("repository", {}).get("full_name", "")
    if not repo:
        repo = os.environ.get("GITHUB_REPOSITORY", "")

    logger.info(f"Repository: {repo}")

    # Run the responder
    try:
        result = await run_issue_responder(issue, repo)

        response_data = result.get("response", {})
        confidence = response_data.get("confidence", 0)
        response_text = response_data.get("content", "")
        should_post = response_data.get("should_auto_post", False)

        logger.info(f"Response generated with confidence: {confidence}")
        logger.info(f"Should auto-post: {should_post}")

        # Set outputs
        set_output("confidence", str(confidence))
        set_output("response", response_text)
        set_output("issue-number", str(issue_number))

        # Post if appropriate
        if should_post and not dry_run and response_text:
            github = GitHubClient(repo=repo)
            github.post_comment(issue_number, response_text)

            # Add suggested labels if any
            labels = response_data.get("suggested_labels", [])
            if labels:
                github.add_labels(issue_number, labels)

            logger.info("Response posted successfully")
            set_output("responded", "true")
        else:
            if dry_run:
                logger.info("Dry run - not posting")
            elif not should_post:
                logger.info(f"Confidence {confidence} below threshold, not posting")
            set_output("responded", "false")

    except Exception as e:
        logger.error(f"Error processing issue: {e}")
        set_output("responded", "false")
        raise


if __name__ == "__main__":
    asyncio.run(main())
