# Sugar MCP Server Implementation Guide

This document outlines the implementation plan for the Sugar MCP (Model Context Protocol) server that bridges Claude Code with Sugar's Python CLI.

## Architecture Overview

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│ Claude Code │ ◄─────► │ MCP Server   │ ◄─────► │ Sugar CLI   │
│   (Client)  │  JSON   │ (Node.js)    │  spawn  │  (Python)   │
└─────────────┘         └──────────────┘         └─────────────┘
                              │
                              ▼
                        ┌──────────────┐
                        │ .sugar/      │
                        │  - sugar.db  │
                        │  - config    │
                        │  - logs      │
                        └──────────────┘
```

## MCP Server Specification

### File: `mcp-server/sugar-mcp.js`

```javascript
#!/usr/bin/env node

import { spawn } from 'child_process';
import { promisify } from 'util';
import { access, constants } from 'fs';
import path from 'path';

const accessAsync = promisify(access);

/**
 * Sugar MCP Server
 * Bridges Claude Code with Sugar's Python CLI
 */
class SugarMCPServer {
  constructor() {
    this.sugarCommand = null;
    this.projectRoot = process.cwd();
  }

  /**
   * Initialize the MCP server
   */
  async initialize() {
    console.log('Sugar MCP Server initializing...');

    // Detect Sugar installation
    this.sugarCommand = await this.detectSugarCommand();

    if (!this.sugarCommand) {
      throw new Error('Sugar CLI not found. Please install: pip install sugarai');
    }

    // Verify Sugar is initialized in project
    const sugarDir = path.join(this.projectRoot, '.sugar');
    try {
      await accessAsync(sugarDir, constants.F_OK);
    } catch {
      console.warn('Sugar not initialized in project. Run: sugar init');
    }

    console.log(`Sugar MCP Server ready. Using: ${this.sugarCommand}`);
  }

  /**
   * Detect Sugar CLI command location
   */
  async detectSugarCommand() {
    const candidates = [
      'sugar',
      '/usr/local/bin/sugar',
      path.join(process.env.HOME, '.local', 'bin', 'sugar'),
      './venv/bin/sugar'
    ];

    for (const cmd of candidates) {
      try {
        const result = await this.execSugar(cmd, ['--version']);
        if (result.success) {
          return cmd;
        }
      } catch {
        continue;
      }
    }

    return null;
  }

  /**
   * Execute Sugar CLI command
   */
  async execSugar(command, args, options = {}) {
    return new Promise((resolve, reject) => {
      const proc = spawn(command, args, {
        cwd: options.cwd || this.projectRoot,
        env: { ...process.env, ...options.env }
      });

      let stdout = '';
      let stderr = '';

      proc.stdout.on('data', (data) => {
        stdout += data.toString();
      });

      proc.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      proc.on('close', (code) => {
        resolve({
          success: code === 0,
          code,
          stdout,
          stderr
        });
      });

      proc.on('error', (error) => {
        reject(error);
      });
    });
  }

  /**
   * MCP Tool Handlers
   */

  async createTask(params) {
    const {
      title,
      type = 'feature',
      priority = 3,
      urgent = false,
      description = null,
      json_data = null
    } = params;

    const args = ['add', title];

    if (type) args.push('--type', type);
    if (priority) args.push('--priority', priority.toString());
    if (urgent) args.push('--urgent');
    if (description && json_data) {
      args.push('--json', '--description', JSON.stringify(json_data));
    } else if (description) {
      args.push('--description', description);
    }

    const result = await this.execSugar(this.sugarCommand, args);

    if (result.success) {
      // Parse task ID from output
      const match = result.stdout.match(/Task created: (.+)/);
      const taskId = match ? match[1] : null;

      return {
        success: true,
        taskId,
        message: 'Task created successfully',
        output: result.stdout
      };
    } else {
      return {
        success: false,
        error: result.stderr,
        message: 'Failed to create task'
      };
    }
  }

  async listTasks(params = {}) {
    const {
      status = null,
      type = null,
      priority = null,
      limit = 20
    } = params;

    const args = ['list'];

    if (status) args.push('--status', status);
    if (type) args.push('--type', type);
    if (priority) args.push('--priority', priority.toString());
    if (limit) args.push('--limit', limit.toString());

    const result = await this.execSugar(this.sugarCommand, args);

    if (result.success) {
      return {
        success: true,
        tasks: this.parseTasks(result.stdout),
        output: result.stdout
      };
    } else {
      return {
        success: false,
        error: result.stderr
      };
    }
  }

  async viewTask(params) {
    const { taskId } = params;

    const result = await this.execSugar(this.sugarCommand, ['view', taskId]);

    if (result.success) {
      return {
        success: true,
        task: this.parseTaskDetails(result.stdout),
        output: result.stdout
      };
    } else {
      return {
        success: false,
        error: result.stderr
      };
    }
  }

  async updateTask(params) {
    const {
      taskId,
      title = null,
      type = null,
      priority = null,
      status = null,
      description = null
    } = params;

    const args = ['update', taskId];

    if (title) args.push('--title', title);
    if (type) args.push('--type', type);
    if (priority) args.push('--priority', priority.toString());
    if (status) args.push('--status', status);
    if (description) args.push('--description', description);

    const result = await this.execSugar(this.sugarCommand, args);

    return {
      success: result.success,
      message: result.success ? 'Task updated successfully' : 'Failed to update task',
      output: result.stdout,
      error: result.stderr
    };
  }

  async getStatus() {
    const result = await this.execSugar(this.sugarCommand, ['status']);

    if (result.success) {
      return {
        success: true,
        status: this.parseStatus(result.stdout),
        output: result.stdout
      };
    } else {
      return {
        success: false,
        error: result.stderr
      };
    }
  }

  async runOnce(params = {}) {
    const { dryRun = false, validate = false } = params;

    const args = ['run', '--once'];
    if (dryRun) args.push('--dry-run');
    if (validate) args.push('--validate');

    const result = await this.execSugar(this.sugarCommand, args);

    return {
      success: result.success,
      output: result.stdout,
      error: result.stderr
    };
  }

  /**
   * Parsing utilities
   */

  parseTasks(output) {
    // Parse Sugar task list output
    // Format: [status] Title (ID: task-xxx)
    const tasks = [];
    const lines = output.split('\n');

    for (const line of lines) {
      const match = line.match(/\[(.*?)\] (.*?) \(ID: (.*?)\)/);
      if (match) {
        tasks.push({
          status: match[1],
          title: match[2],
          id: match[3]
        });
      }
    }

    return tasks;
  }

  parseTaskDetails(output) {
    // Parse detailed task information
    // This would parse the `sugar view` output
    return {
      raw: output
      // TODO: Parse structured details
    };
  }

  parseStatus(output) {
    // Parse `sugar status` output
    return {
      raw: output
      // TODO: Parse structured status
    };
  }
}

/**
 * MCP Server Entry Point
 */
async function main() {
  const server = new SugarMCPServer();

  try {
    await server.initialize();

    // MCP communication loop
    process.stdin.on('data', async (data) => {
      try {
        const request = JSON.parse(data.toString());
        let response;

        switch (request.method) {
          case 'createTask':
            response = await server.createTask(request.params);
            break;
          case 'listTasks':
            response = await server.listTasks(request.params);
            break;
          case 'viewTask':
            response = await server.viewTask(request.params);
            break;
          case 'updateTask':
            response = await server.updateTask(request.params);
            break;
          case 'getStatus':
            response = await server.getStatus();
            break;
          case 'runOnce':
            response = await server.runOnce(request.params);
            break;
          default:
            response = {
              success: false,
              error: `Unknown method: ${request.method}`
            };
        }

        process.stdout.write(JSON.stringify(response) + '\n');
      } catch (error) {
        process.stdout.write(JSON.stringify({
          success: false,
          error: error.message
        }) + '\n');
      }
    });

  } catch (error) {
    console.error('Failed to initialize Sugar MCP Server:', error);
    process.exit(1);
  }
}

main();
```

### Package Configuration: `mcp-server/package.json`

```json
{
  "name": "sugar-mcp-server",
  "version": "1.9.1",
  "description": "MCP server for Sugar autonomous development system",
  "type": "module",
  "main": "sugar-mcp.js",
  "bin": {
    "sugar-mcp": "./sugar-mcp.js"
  },
  "scripts": {
    "start": "node sugar-mcp.js",
    "test": "node --test"
  },
  "keywords": ["sugar", "claude-code", "mcp", "autonomous-development"],
  "author": "Steven Leggett <contact@roboticforce.io>",
  "license": "MIT",
  "engines": {
    "node": ">=16.0.0"
  },
  "dependencies": {},
  "devDependencies": {
    "eslint": "^8.0.0"
  }
}
```

### MCP Server Declaration: `.mcp.json`

```json
{
  "mcpServers": {
    "sugar": {
      "command": "node",
      "args": ["./mcp-server/sugar-mcp.js"],
      "env": {
        "SUGAR_PROJECT_ROOT": "${workspaceFolder}"
      },
      "schema": {
        "methods": {
          "createTask": {
            "description": "Create a new Sugar task",
            "params": {
              "title": {"type": "string", "required": true},
              "type": {"type": "string", "enum": ["bug_fix", "feature", "test", "refactor", "documentation"]},
              "priority": {"type": "number", "min": 1, "max": 5},
              "urgent": {"type": "boolean"},
              "description": {"type": "string"},
              "json_data": {"type": "object"}
            }
          },
          "listTasks": {
            "description": "List Sugar tasks",
            "params": {
              "status": {"type": "string", "enum": ["pending", "active", "completed", "failed"]},
              "type": {"type": "string"},
              "priority": {"type": "number"},
              "limit": {"type": "number"}
            }
          },
          "viewTask": {
            "description": "View detailed task information",
            "params": {
              "taskId": {"type": "string", "required": true}
            }
          },
          "updateTask": {
            "description": "Update an existing task",
            "params": {
              "taskId": {"type": "string", "required": true},
              "title": {"type": "string"},
              "type": {"type": "string"},
              "priority": {"type": "number"},
              "status": {"type": "string"},
              "description": {"type": "string"}
            }
          },
          "getStatus": {
            "description": "Get Sugar system status"
          },
          "runOnce": {
            "description": "Execute one autonomous cycle",
            "params": {
              "dryRun": {"type": "boolean"},
              "validate": {"type": "boolean"}
            }
          }
        }
      }
    }
  }
}
```

## Installation Steps

### 1. Install Sugar CLI
```bash
pip install sugarai
```

### 2. Install MCP Server
```bash
cd .claude-plugin/mcp-server
npm install
```

### 3. Configure Claude Code
The `.mcp.json` file will be automatically detected by Claude Code when the plugin is installed.

### 4. Verify Installation
```bash
# Test MCP server directly
echo '{"method":"getStatus","params":{}}' | node mcp-server/sugar-mcp.js

# Should return Sugar status JSON
```

## Usage Examples

### From Claude Code Conversations

Claude Code will automatically use the MCP server when slash commands are invoked:

```
User: /sugar-task "Fix authentication bug" --urgent
→ MCP calls createTask({title: "...", urgent: true})
→ Sugar CLI executes: sugar add "..." --urgent
→ Result returned to Claude
```

### Programmatic Access

```javascript
// Example of calling MCP methods programmatically
const request = {
  method: 'createTask',
  params: {
    title: 'Implement OAuth2',
    type: 'feature',
    priority: 4,
    json_data: {
      context: 'Add OAuth2 authentication',
      agent_assignments: {
        backend_developer: 'Implementation',
        qa_test_engineer: 'Testing'
      }
    }
  }
};

// Send via stdin, receive via stdout
```

## Testing

### Unit Tests: `mcp-server/test/sugar-mcp.test.js`

```javascript
import { test } from 'node:test';
import { strict as assert } from 'node:assert';
import { SugarMCPServer } from '../sugar-mcp.js';

test('Sugar MCP Server - Task parsing', async () => {
  const server = new SugarMCPServer();
  const output = '[pending] Fix auth bug (ID: task-123)\n[active] Add tests (ID: task-124)';

  const tasks = server.parseTasks(output);

  assert.equal(tasks.length, 2);
  assert.equal(tasks[0].id, 'task-123');
  assert.equal(tasks[0].status, 'pending');
});

// More tests...
```

### Integration Tests

```bash
# Test with actual Sugar CLI
npm test -- --integration
```

## Error Handling

The MCP server handles:
- Sugar CLI not installed
- Sugar not initialized in project
- Command execution failures
- Invalid parameters
- JSON parsing errors
- Process spawn errors

## Performance Considerations

- **Process Pooling**: For frequent operations, consider keeping a Sugar CLI process alive
- **Caching**: Cache Sugar status for short periods
- **Async Operations**: All Sugar CLI calls are non-blocking
- **Timeouts**: Add timeouts for long-running operations

## Security

- **Command Injection**: All parameters are properly escaped
- **Path Validation**: Project root is validated
- **Environment Isolation**: Each project gets isolated Sugar instance
- **No Sensitive Data**: MCP server doesn't store credentials

## Future Enhancements

1. **WebSocket Support**: Real-time task updates
2. **Streaming Output**: Stream `sugar run` output
3. **Advanced Querying**: SQL-like task queries
4. **Batch Operations**: Multiple task operations in one call
5. **Event Subscriptions**: Subscribe to task changes

## Troubleshooting

### MCP Server Not Starting
```bash
# Check Node.js version
node --version  # Should be >=16

# Test MCP server directly
node mcp-server/sugar-mcp.js
# Should show: "Sugar MCP Server initializing..."
```

### Sugar CLI Not Found
```bash
# Verify Sugar installation
which sugar
sugar --version

# If not found, install
pip install sugarai
```

### Permission Errors
```bash
# Make MCP server executable
chmod +x mcp-server/sugar-mcp.js
```

## Documentation

Complete MCP server documentation at:
- API Reference: `docs/mcp-api-reference.md`
- Integration Guide: `docs/mcp-integration.md`
- Troubleshooting: `docs/mcp-troubleshooting.md`
