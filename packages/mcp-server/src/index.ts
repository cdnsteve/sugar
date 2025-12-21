#!/usr/bin/env node

/**
 * Sugar MCP Server
 *
 * MCP server for Sugar - autonomous AI development system.
 * Exposes Sugar CLI functionality as MCP tools for use with Goose, Claude, and other MCP clients.
 *
 * @see https://github.com/roboticforce/sugar
 * @see https://modelcontextprotocol.io
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { spawn } from "child_process";
import { access, constants } from "fs/promises";
import { join } from "path";
import { homedir } from "os";

const PROJECT_ROOT = process.env.SUGAR_PROJECT_ROOT || process.cwd();
const DEBUG = process.env.SUGAR_DEBUG === "true";

function log(...args: unknown[]): void {
  if (DEBUG) {
    console.error("[Sugar MCP]", ...args);
  }
}

/**
 * Execute a shell command and return the result
 */
async function execCommand(
  command: string,
  args: string[],
  options: { cwd?: string; timeout?: number } = {}
): Promise<{ success: boolean; code: number; stdout: string; stderr: string }> {
  return new Promise((resolve) => {
    const proc = spawn(command, args, {
      cwd: options.cwd || PROJECT_ROOT,
      timeout: options.timeout || 30000,
    });

    let stdout = "";
    let stderr = "";

    proc.stdout?.on("data", (data) => {
      stdout += data.toString();
    });

    proc.stderr?.on("data", (data) => {
      stderr += data.toString();
    });

    proc.on("close", (code) => {
      resolve({
        success: code === 0,
        code: code ?? -1,
        stdout: stdout.trim(),
        stderr: stderr.trim(),
      });
    });

    proc.on("error", (error) => {
      resolve({
        success: false,
        code: -1,
        stdout: "",
        stderr: error.message,
      });
    });
  });
}

/**
 * Detect Sugar CLI command location
 */
async function detectSugarCommand(): Promise<string | null> {
  const candidates = [
    "sugar",
    "/usr/local/bin/sugar",
    join(homedir(), ".local", "bin", "sugar"),
    join(PROJECT_ROOT, "venv", "bin", "sugar"),
    join(PROJECT_ROOT, ".venv", "bin", "sugar"),
  ];

  for (const cmd of candidates) {
    try {
      const result = await execCommand(cmd, ["--version"]);
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
async function execSugar(
  sugarCmd: string,
  args: string[],
  options: { timeout?: number } = {}
): Promise<{ success: boolean; code: number; stdout: string; stderr: string }> {
  return execCommand(sugarCmd, args, { cwd: PROJECT_ROOT, ...options });
}

/**
 * Main entry point
 */
async function main(): Promise<void> {
  log("Sugar MCP Server starting...");
  log(`Project root: ${PROJECT_ROOT}`);

  // Detect Sugar CLI
  const sugarCmd = await detectSugarCommand();
  if (!sugarCmd) {
    console.error(
      "Sugar CLI not found. Please install: pip install sugarai && sugar init"
    );
    process.exit(1);
  }
  log(`Sugar CLI found: ${sugarCmd}`);

  // Check if Sugar is initialized
  try {
    await access(join(PROJECT_ROOT, ".sugar"), constants.F_OK);
    log("Sugar initialized in project");
  } catch {
    log("Warning: Sugar not initialized. Run: sugar init");
  }

  // Create MCP server
  const server = new McpServer({
    name: "sugar",
    version: "1.0.0",
  });

  // Tool: createTask
  server.tool(
    "createTask",
    "Create a new Sugar task for autonomous development",
    {
      title: z.string().describe("Task title (required)"),
      type: z
        .enum(["bug_fix", "feature", "test", "refactor", "documentation"])
        .default("feature")
        .describe("Task type"),
      priority: z
        .number()
        .min(1)
        .max(5)
        .default(3)
        .describe("Priority level (1=low, 5=urgent)"),
      urgent: z
        .boolean()
        .default(false)
        .describe("Mark as urgent (sets priority to 5)"),
      description: z
        .string()
        .optional()
        .describe("Detailed task description"),
    },
    async ({ title, type, priority, urgent, description }) => {
      log("createTask called", { title, type, priority, urgent });

      const args = ["add", title];
      if (type) args.push("--type", type);
      if (priority) args.push("--priority", priority.toString());
      if (urgent) args.push("--urgent");
      if (description) args.push("--description", description);

      const result = await execSugar(sugarCmd, args);

      if (result.success) {
        const match =
          result.stdout.match(/Task (?:created|added).*?:\s*(.+)/i) ||
          result.stdout.match(/ID:\s*(.+)/i);
        const taskId = match ? match[1].trim() : null;

        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify({
                success: true,
                taskId,
                message: "Task created successfully",
                output: result.stdout,
              }),
            },
          ],
        };
      } else {
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify({
                success: false,
                error: result.stderr || result.stdout,
                message: "Failed to create task",
              }),
            },
          ],
          isError: true,
        };
      }
    }
  );

  // Tool: listTasks
  server.tool(
    "listTasks",
    "List Sugar tasks with optional filtering",
    {
      status: z
        .enum(["pending", "hold", "active", "completed", "failed"])
        .optional()
        .describe("Filter by status"),
      type: z.string().optional().describe("Filter by task type"),
      priority: z
        .number()
        .min(1)
        .max(5)
        .optional()
        .describe("Filter by priority"),
      limit: z
        .number()
        .default(20)
        .describe("Maximum number of tasks to return"),
    },
    async ({ status, type, priority, limit }) => {
      log("listTasks called", { status, type, priority, limit });

      const args = ["list"];
      if (status) args.push("--status", status);
      if (type) args.push("--type", type);
      if (priority) args.push("--priority", priority.toString());
      if (limit) args.push("--limit", limit.toString());

      const result = await execSugar(sugarCmd, args);

      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify({
              success: result.success,
              output: result.stdout,
              error: result.stderr || undefined,
            }),
          },
        ],
        isError: !result.success,
      };
    }
  );

  // Tool: viewTask
  server.tool(
    "viewTask",
    "View detailed information about a specific task",
    {
      taskId: z.string().describe("Task ID to view"),
    },
    async ({ taskId }) => {
      log("viewTask called", { taskId });

      const result = await execSugar(sugarCmd, ["view", taskId]);

      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify({
              success: result.success,
              output: result.stdout,
              error: result.stderr || undefined,
            }),
          },
        ],
        isError: !result.success,
      };
    }
  );

  // Tool: updateTask
  server.tool(
    "updateTask",
    "Update an existing Sugar task",
    {
      taskId: z.string().describe("Task ID to update"),
      title: z.string().optional().describe("New task title"),
      type: z.string().optional().describe("New task type"),
      priority: z
        .number()
        .min(1)
        .max(5)
        .optional()
        .describe("New priority level"),
      status: z
        .enum(["pending", "hold", "active", "completed", "failed"])
        .optional()
        .describe("New status"),
      description: z.string().optional().describe("New description"),
    },
    async ({ taskId, title, type, priority, status, description }) => {
      log("updateTask called", { taskId, title, type, priority, status });

      const args = ["update", taskId];
      if (title) args.push("--title", title);
      if (type) args.push("--type", type);
      if (priority) args.push("--priority", priority.toString());
      if (status) args.push("--status", status);
      if (description) args.push("--description", description);

      const result = await execSugar(sugarCmd, args);

      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify({
              success: result.success,
              message: result.success
                ? "Task updated successfully"
                : "Failed to update task",
              output: result.stdout,
              error: result.stderr || undefined,
            }),
          },
        ],
        isError: !result.success,
      };
    }
  );

  // Tool: removeTask
  server.tool(
    "removeTask",
    "Remove a task from the queue",
    {
      taskId: z.string().describe("Task ID to remove"),
    },
    async ({ taskId }) => {
      log("removeTask called", { taskId });

      const result = await execSugar(sugarCmd, ["remove", taskId]);

      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify({
              success: result.success,
              message: result.success
                ? "Task removed successfully"
                : "Failed to remove task",
              output: result.stdout,
              error: result.stderr || undefined,
            }),
          },
        ],
        isError: !result.success,
      };
    }
  );

  // Tool: getStatus
  server.tool(
    "getStatus",
    "Get Sugar system status and task queue metrics",
    {},
    async () => {
      log("getStatus called");

      const result = await execSugar(sugarCmd, ["status"]);

      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify({
              success: result.success,
              output: result.stdout,
              error: result.stderr || undefined,
            }),
          },
        ],
        isError: !result.success,
      };
    }
  );

  // Tool: runOnce
  server.tool(
    "runOnce",
    "Execute one autonomous development cycle (picks up highest priority task)",
    {
      dryRun: z
        .boolean()
        .default(false)
        .describe("Simulate execution without making changes"),
      validate: z
        .boolean()
        .default(false)
        .describe("Validate configuration before running"),
    },
    async ({ dryRun, validate }) => {
      log("runOnce called", { dryRun, validate });

      const args = ["run", "--once"];
      if (dryRun) args.push("--dry-run");
      if (validate) args.push("--validate");

      // Longer timeout for execution
      const result = await execSugar(sugarCmd, args, { timeout: 300000 });

      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify({
              success: result.success,
              output: result.stdout,
              error: result.stderr || undefined,
            }),
          },
        ],
        isError: !result.success,
      };
    }
  );

  // Tool: initSugar
  server.tool(
    "initSugar",
    "Initialize Sugar in the current project directory",
    {},
    async () => {
      log("initSugar called");

      const result = await execSugar(sugarCmd, ["init"]);

      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify({
              success: result.success,
              message: result.success
                ? "Sugar initialized successfully"
                : "Failed to initialize Sugar",
              output: result.stdout,
              error: result.stderr || undefined,
            }),
          },
        ],
        isError: !result.success,
      };
    }
  );

  // Connect via stdio transport
  const transport = new StdioServerTransport();
  await server.connect(transport);

  log("Sugar MCP Server ready");
}

main().catch((error) => {
  console.error("Failed to start Sugar MCP Server:", error);
  process.exit(1);
});
