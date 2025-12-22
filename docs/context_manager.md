# Context Manager

The ContextManager provides intelligent conversation context management with automatic summarization for long-running agent conversations.

## Overview

As AI agents handle longer conversations, managing context becomes critical to:
- Stay within token limits
- Reduce API costs
- Maintain conversation coherence
- Preserve important information

The ContextManager solves this by:
1. Tracking all messages and their token counts
2. Automatically triggering summarization when thresholds are exceeded
3. Using Claude Haiku for fast, cost-effective summarization
4. Preserving recent messages in full while summarizing older context
5. Extracting and preserving key decisions and file modifications

## Installation

The ContextManager is included in Sugar's agent module. For summarization features, you'll need:

```bash
pip install anthropic  # For Claude API access
pip install tiktoken   # For accurate token counting (optional)
```

## Basic Usage

```python
from sugar.agent import ContextManager

# Create a context manager
manager = ContextManager(
    token_threshold=150000,  # Trigger summarization at 150k tokens
    preserve_recent=10,       # Keep last 10 messages in full
    summarization_model="claude-3-haiku-20240307"
)

# Add messages as conversation progresses
manager.add_message("user", "Build a user authentication system")
manager.add_message("assistant", "I'll create auth.py with JWT support...")

# Get context for the agent (includes summaries if any)
context = manager.get_context()
# Returns: [{"role": "user", "content": "..."}, ...]

# Check if summarization is needed and trigger it
summary = await manager.trigger_summarization_if_needed()

# Get statistics
stats = manager.get_stats()
print(f"Total tokens: {stats['total_tokens']}")
print(f"Tokens saved: {stats['total_tokens_saved']}")
```

## Configuration

### Token Threshold

The token limit before triggering summarization:

```python
manager = ContextManager(token_threshold=150000)
```

- Default: 150,000 tokens (~100k words)
- Claude's context window is 200k tokens, so 150k provides a safety margin
- Adjust based on your use case and model

### Preserve Recent

Number of recent messages to keep in full (not summarized):

```python
manager = ContextManager(preserve_recent=10)
```

- Default: 10 messages
- Recent messages are more relevant, so we preserve them
- Older messages get summarized

### Summarization Model

The Claude model used for generating summaries:

```python
manager = ContextManager(summarization_model="claude-3-haiku-20240307")
```

- Default: Claude 3 Haiku (fast and cost-effective)
- Can use other models, but Haiku is recommended for cost

## Features

### Automatic Token Counting

The ContextManager automatically counts tokens:

```python
manager.add_message("user", "Some message")
# Tokens are counted automatically
```

Token counting uses:
1. **tiktoken** if available (accurate)
2. **Character approximation** as fallback (chars / 4)

### Key Decision Extraction

Automatically extracts important decisions from conversations:

```python
decisions = manager._extract_key_decisions(messages)
# Returns: ["implement JWT authentication", "use Redis for caching", ...]
```

Patterns detected:
- "decided to..."
- "will implement..."
- "chose to..."
- "going to..."
- "plan to..."
- "approach is to..."

### File Path Extraction

Tracks files mentioned in the conversation:

```python
files = manager._extract_files_modified(messages)
# Returns: ["auth.py", "config.py", "middleware.py"]
```

Extracts from:
- Tool use parameters (`file_path: "auth.py"`)
- Natural language ("I modified auth.py")
- Code blocks with file references

### Summarization

When token threshold is exceeded:

```python
# Automatic trigger on add_message
manager.add_message("user", "Long message...")  # May set flag

# Manual trigger
summary = await manager.trigger_summarization_if_needed()

if summary:
    print(f"Summarized {summary.messages_summarized} messages")
    print(f"Reduced from {summary.original_token_count} to {summary.summarized_token_count} tokens")
    print(f"Saved {summary.original_token_count - summary.summarized_token_count} tokens")
```

The summarization process:
1. Selects older messages (preserving recent N)
2. Extracts key decisions and files
3. Calls Claude Haiku with summarization prompt
4. Replaces old messages with summary
5. Updates statistics

### State Persistence

Export and import state for persistence:

```python
# Export
state = manager.export_state()
# Save to file/database
import json
with open('context_state.json', 'w') as f:
    json.dump(state, f)

# Import
with open('context_state.json', 'r') as f:
    state = json.load(f)
manager.import_state(state)
```

## Statistics

Track context usage:

```python
stats = manager.get_stats()
```

Returns:
- `total_messages`: Number of current messages
- `total_tokens`: Current token count
- `token_threshold`: Configured threshold
- `threshold_percentage`: How close to threshold (%)
- `summaries_created`: Number of summaries generated
- `total_tokens_saved`: Total tokens saved by summarization
- `messages_in_summaries`: Total messages that have been summarized
- `summarization_enabled`: Whether Anthropic client is available

## Integration with SugarAgent

```python
from sugar.agent import SugarAgent, SugarAgentConfig, ContextManager

# Create context manager
context_manager = ContextManager()

# Create agent
config = SugarAgentConfig(model="claude-sonnet-4-20250514")
agent = SugarAgent(config)

# In your conversation loop
async def conversation_loop():
    while True:
        user_input = get_user_input()

        # Add user message to context
        context_manager.add_message("user", user_input)

        # Check if summarization needed
        await context_manager.trigger_summarization_if_needed()

        # Get context for agent
        context = context_manager.get_context()

        # Execute agent with context
        response = await agent.execute(user_input)

        # Add assistant response to context
        context_manager.add_message("assistant", response.content)
```

## Error Handling

The ContextManager gracefully handles errors:

### No Anthropic SDK

```python
# Summarization will be disabled
manager = ContextManager()
# manager._anthropic_client will be None
# Summaries won't be created, but everything else works
```

### API Errors

```python
summary = await manager.trigger_summarization_if_needed()
if summary is None:
    # Summarization failed or wasn't needed
    # Check logs for details
    pass
```

### No tiktoken

```python
# Falls back to character-based approximation
# Less accurate but functional
```

## Best Practices

1. **Set appropriate thresholds**: Leave room below model's context window
2. **Preserve enough recent messages**: 10-20 is usually good
3. **Monitor statistics**: Check `threshold_percentage` regularly
4. **Handle API failures gracefully**: Summarization might fail occasionally
5. **Persist state**: Export state between sessions for continuity
6. **Use Haiku for summarization**: It's fast and cheap

## Performance

### Token Counting
- With tiktoken: ~10,000 messages/second
- Without tiktoken: ~50,000 messages/second (approximation)

### Summarization
- Claude Haiku: ~500ms per summarization
- Cost: ~$0.001 per 1000 messages summarized

### Memory
- ~1KB per message (content-dependent)
- Summaries reduce memory by ~80%

## Example Use Cases

### Long-running development sessions
```python
manager = ContextManager(token_threshold=150000, preserve_recent=20)
# Track entire development session
# Summarize when needed
# Preserve recent context for continuity
```

### Interactive debugging
```python
manager = ContextManager(token_threshold=50000, preserve_recent=5)
# Shorter threshold for faster cycles
# Keep recent debugging steps
# Summarize earlier context
```

### Multi-task workflows
```python
manager = ContextManager(token_threshold=100000, preserve_recent=15)
# Track multiple related tasks
# Preserve task transitions
# Summarize completed tasks
```

## Limitations

1. **Summarization requires Anthropic SDK**: Won't work without it
2. **API costs**: Each summarization calls Claude Haiku
3. **Information loss**: Summaries are lossy compression
4. **Latency**: Summarization adds ~500ms when triggered
5. **Single-threaded**: Not designed for concurrent access

## Future Enhancements

Potential improvements:
- Local summarization models (no API required)
- Semantic chunking (cluster related messages)
- Multi-level summaries (summaries of summaries)
- Streaming summarization (incremental updates)
- Custom extraction patterns (user-defined)
- Parallel summarization (faster for large contexts)

## See Also

- [SugarAgent Documentation](./agent.md)
- [Quality Gates](./quality_gates.md)
- [Examples](../examples/context_manager_demo.py)
