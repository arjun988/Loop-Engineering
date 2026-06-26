/**
 * MCP Server implementation for Loop Engineering
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import * as fs from 'fs/promises';
import * as path from 'path';
import { LoopManager } from './loop-manager.js';
import { SkillManager } from './skill-manager.js';
import { StateManager } from './state-manager.js';
import { LoopLogger } from './logger.js';
import { LoopExecutor } from './loop-executor.js';
import { LoopScheduler } from './scheduler.js';
import { VerificationRunner } from './verification-runner.js';

export function createServer(startScheduler = true) {
  const server = new Server(
    { name: 'loop-engineering', version: '0.1.0' },
    { capabilities: { tools: {} } }
  );

  const workspaceRoot = process.cwd();
  const loopDir = path.join(workspaceRoot, '.loop');

  const loopManager = new LoopManager(loopDir);
  const skillManager = new SkillManager(path.join(loopDir, 'skills'));
  const stateManager = new StateManager(path.join(loopDir, 'state'));
  const logger = new LoopLogger(path.join(loopDir, 'logs'));
  const executor = new LoopExecutor(
    workspaceRoot,
    loopManager,
    skillManager,
    stateManager,
    logger
  );
  const verificationRunner = new VerificationRunner(workspaceRoot);

  const scheduler = startScheduler
    ? new LoopScheduler(loopManager, logger, (name) => executor.queueRun(name))
    : null;

  fs.mkdir(path.join(loopDir, 'logs'), { recursive: true }).catch(() => {});

  server.setRequestHandler(ListToolsRequestSchema, async () => ({
    tools: [
      {
        name: 'create_loop',
        description: 'Create a new automated loop with skill template and state tracking',
        inputSchema: {
          type: 'object',
          properties: {
            name: { type: 'string', description: "Loop identifier (e.g., 'ci-triage')" },
            description: { type: 'string', description: 'What this loop does' },
            schedule: { type: 'string', description: "Cron expression (e.g., '0 */6 * * *')" },
            skill_instructions: { type: 'string', description: 'Detailed instructions for the AI agent' },
            verification_command: { type: 'string', description: "Command to verify changes (e.g., 'npm test')" },
            goal: { type: 'string', description: 'Success criteria for each run' },
          },
          required: ['name', 'description', 'schedule', 'skill_instructions', 'goal'],
        },
      },
      {
        name: 'start_loop',
        description: 'Start or resume a loop (activates cron scheduler)',
        inputSchema: {
          type: 'object',
          properties: { name: { type: 'string', description: 'Loop name to start' } },
          required: ['name'],
        },
      },
      {
        name: 'stop_loop',
        description: "Stop a running loop (doesn't delete it)",
        inputSchema: {
          type: 'object',
          properties: { name: { type: 'string', description: 'Loop name to stop' } },
          required: ['name'],
        },
      },
      {
        name: 'run_loop_now',
        description:
          'Begin a loop run — returns skill instructions for YOU (the host agent) to execute. After making changes, call complete_loop_run.',
        inputSchema: {
          type: 'object',
          properties: {
            name: { type: 'string', description: 'Loop name to run' },
            create_pr: { type: 'boolean', description: 'Whether to create a PR when complete (default: true)' },
          },
          required: ['name'],
        },
      },
      {
        name: 'complete_loop_run',
        description:
          'Finalize a loop run after you (host agent) have made code changes. Runs verification, opens PR, updates state.',
        inputSchema: {
          type: 'object',
          properties: {
            loop_name: { type: 'string', description: 'Loop name' },
            run_id: { type: 'string', description: 'Run ID from run_loop_now' },
            summary: { type: 'string', description: 'What you changed' },
            create_pr: { type: 'boolean', description: 'Override PR creation' },
          },
          required: ['loop_name', 'run_id', 'summary'],
        },
      },
      {
        name: 'list_pending_runs',
        description: 'Show loops queued by the scheduler waiting for a host agent session',
        inputSchema: { type: 'object', properties: {} },
      },
      {
        name: 'run_verification',
        description: 'Run the verification command for a loop',
        inputSchema: {
          type: 'object',
          properties: { loop_name: { type: 'string', description: 'Loop name' } },
          required: ['loop_name'],
        },
      },
      {
        name: 'list_loops',
        description: 'Show all loops with status, metrics, and recent activity',
        inputSchema: { type: 'object', properties: {} },
      },
      {
        name: 'delete_loop',
        description: 'Permanently delete a loop and its state',
        inputSchema: {
          type: 'object',
          properties: { name: { type: 'string', description: 'Loop name to delete' } },
          required: ['name'],
        },
      },
      {
        name: 'add_skill',
        description: 'Create a reusable skill template',
        inputSchema: {
          type: 'object',
          properties: {
            name: { type: 'string' },
            description: { type: 'string' },
            instructions: { type: 'string' },
            project_context: { type: 'object' },
          },
          required: ['name', 'description', 'instructions'],
        },
      },
      { name: 'list_skills', description: 'Show all available skill templates', inputSchema: { type: 'object', properties: {} } },
      {
        name: 'view_state',
        description: 'Show detailed state for a specific loop',
        inputSchema: {
          type: 'object',
          properties: { name: { type: 'string', description: 'Loop name' } },
          required: ['name'],
        },
      },
      {
        name: 'add_lesson',
        description: 'Record a lesson learned for future loop runs',
        inputSchema: {
          type: 'object',
          properties: {
            loop_name: { type: 'string' },
            lesson: { type: 'string' },
          },
          required: ['loop_name', 'lesson'],
        },
      },
      { name: 'get_metrics', description: 'Get aggregated metrics across all loops', inputSchema: { type: 'object', properties: {} } },
      {
        name: 'configure_verification',
        description: 'Set or update verification command for a loop',
        inputSchema: {
          type: 'object',
          properties: {
            loop_name: { type: 'string' },
            command: { type: 'string' },
          },
          required: ['loop_name', 'command'],
        },
      },
    ],
  }));

  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    try {
      const { name, arguments: args } = request.params;
      const a = args as Record<string, string | boolean>;

      switch (name) {
        case 'create_loop': {
          const result = await loopManager.createLoop(
            a.name as string,
            a.description as string,
            a.schedule as string,
            a.skill_instructions as string,
            a.goal as string,
            a.verification_command as string | undefined
          );
          await skillManager.createSkill(a.name as string, a.description as string, a.skill_instructions as string);
          await stateManager.initializeState(a.name as string);
          await logger.info('loop_created', a.name as string);
          return { content: [{ type: 'text', text: result }] };
        }
        case 'start_loop': {
          const result = await loopManager.startLoop(a.name as string);
          if (scheduler) scheduler.start();
          await logger.info('loop_started', a.name as string);
          return { content: [{ type: 'text', text: result }] };
        }
        case 'stop_loop': {
          const result = await loopManager.stopLoop(a.name as string);
          await logger.info('loop_stopped', a.name as string);
          return { content: [{ type: 'text', text: result }] };
        }
        case 'run_loop_now': {
          const createPr = a.create_pr !== false;
          const result = await executor.beginRun(a.name as string, { createPr });
          return { content: [{ type: 'text', text: result }] };
        }
        case 'complete_loop_run': {
          const result = await executor.completeRun(
            a.loop_name as string,
            a.run_id as string,
            a.summary as string,
            { createPr: a.create_pr as boolean | undefined }
          );
          return { content: [{ type: 'text', text: result }] };
        }
        case 'list_pending_runs':
          return { content: [{ type: 'text', text: await stateManager.listPendingRuns() }] };
        case 'run_verification': {
          const loops = await loopManager.loadLoopsInternal();
          const loopName = a.loop_name as string;
          if (!loops[loopName]) {
            return { content: [{ type: 'text', text: `❌ Loop '${loopName}' not found.` }] };
          }
          const cmd = loops[loopName].verification_command ?? '';
          const verification = await verificationRunner.run(cmd);
          const status = verification.success ? '✅ Passed' : '❌ Failed';
          let result = `**Verification for '${loopName}'**\n**Command:** ${cmd}\n**Result:** ${status}\n**Exit code:** ${verification.exitCode}\n**Duration:** ${verification.durationSeconds.toFixed(1)}s\n`;
          if (verification.stdout) result += `\n**Stdout:**\n\`\`\`\n${verification.stdout.slice(0, 2000)}\n\`\`\`\n`;
          if (verification.stderr) result += `\n**Stderr:**\n\`\`\`\n${verification.stderr.slice(0, 2000)}\n\`\`\`\n`;
          return { content: [{ type: 'text', text: result }] };
        }
        case 'list_loops':
          return { content: [{ type: 'text', text: await loopManager.listLoops() }] };
        case 'delete_loop': {
          const result = await loopManager.deleteLoop(a.name as string);
          await skillManager.deleteSkill(a.name as string);
          await stateManager.deleteState(a.name as string);
          await logger.info('loop_deleted', a.name as string);
          return { content: [{ type: 'text', text: result }] };
        }
        case 'add_skill':
          return {
            content: [
              {
                type: 'text',
                text: await skillManager.createSkill(
                  a.name as string,
                  a.description as string,
                  a.instructions as string,
                  a.project_context as unknown as Record<string, unknown> | undefined
                ),
              },
            ],
          };
        case 'list_skills':
          return { content: [{ type: 'text', text: await skillManager.listSkills() }] };
        case 'view_state':
          return { content: [{ type: 'text', text: await stateManager.getState(a.name as string) }] };
        case 'add_lesson':
          return {
            content: [{ type: 'text', text: await stateManager.addLesson(a.loop_name as string, a.lesson as string) }],
          };
        case 'get_metrics':
          return { content: [{ type: 'text', text: await stateManager.getMetrics() }] };
        case 'configure_verification':
          return {
            content: [
              {
                type: 'text',
                text: await loopManager.configureVerification(a.loop_name as string, a.command as string),
              },
            ],
          };
        default:
          throw new Error(`Unknown tool: ${name}`);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      return { content: [{ type: 'text', text: `Error: ${errorMessage}` }], isError: true };
    }
  });

  return { server, scheduler };
}
