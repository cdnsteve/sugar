# sugarai-mcp

MCP server for [Sugar](https://github.com/cdnsteve/sugar) - autonomous AI development system.

## What is Sugar?

Sugar is an AI-powered autonomous development system that runs 24/7, executing development tasks in the background. It discovers work from error logs, GitHub issues, and code analysis, then implements fixes and features autonomously.

## Installation

### Prerequisites

- Node.js 18+
- Python 3.11+
- Sugar CLI installed: `pip install sugarai`

### Using with Goose

```bash
# Add to Goose via CLI
goose configure

# Select "Add Extension" → "Command-line Extension"
# Name: sugar
# Command: npx -y sugarai-mcp
```

Or add directly to your Goose config (`~/.config/goose/config.yaml`):

```yaml
extensions:
  sugar:
    command: npx
    args: ["-y", "sugarai-mcp"]
    env:
      SUGAR_PROJECT_ROOT: /path/to/your/project
```

### Using with Claude Desktop

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "sugar": {
      "command": "npx",
      "args": ["-y", "sugarai-mcp"],
      "env": {
        "SUGAR_PROJECT_ROOT": "/path/to/your/project"
      }
    }
  }
}
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SUGAR_PROJECT_ROOT` | Project directory for Sugar operations | Current working directory |
| `SUGAR_DEBUG` | Enable debug logging (`true`/`false`) | `false` |

## Available Tools

| Tool | Description |
|------|-------------|
| `createTask` | Create a new development task |
| `listTasks` | List tasks with optional filtering |
| `viewTask` | View detailed task information |
| `updateTask` | Update task status, priority, etc. |
| `removeTask` | Remove a task from the queue |
| `getStatus` | Get Sugar system status and metrics |
| `runOnce` | Execute one autonomous development cycle |
| `initSugar` | Initialize Sugar in the project |

## Examples

### Create a Task

```
Create a task to fix the authentication timeout bug with high priority
```

Sugar will create a task that can be picked up by the autonomous loop.

### Check Status

```
What's the current status of Sugar tasks?
```

### Run Autonomous Cycle

```
Run one Sugar development cycle to work on the highest priority task
```

## Development

```bash
# Clone the repo
git clone https://github.com/cdnsteve/sugar.git
cd sugar/packages/mcp-server

# Install dependencies
npm install

# Build
npm run build

# Run locally
node dist/index.js
```

## License

MIT
