/**
 * Orchestrates loop runs via the host agent (Cursor/Kiro) — no external AI API calls
 */

import * as fs from 'fs/promises';
import * as path from 'path';
import { execSync } from 'child_process';
import { randomUUID } from 'crypto';
import { GitHubClient, PullRequestResult } from './github-client.js';
import { LoopLogger } from './logger.js';
import { LoopManager } from './loop-manager.js';
import { SkillManager } from './skill-manager.js';
import { StateManager } from './state-manager.js';
import { VerificationRunner } from './verification-runner.js';

export class LoopExecutor {
  private workspaceRoot: string;
  private loopManager: LoopManager;
  private skillManager: SkillManager;
  private stateManager: StateManager;
  private logger: LoopLogger;
  private verificationRunner: VerificationRunner;
  private githubClient: GitHubClient;

  constructor(
    workspaceRoot: string,
    loopManager: LoopManager,
    skillManager: SkillManager,
    stateManager: StateManager,
    logger: LoopLogger
  ) {
    this.workspaceRoot = workspaceRoot;
    this.loopManager = loopManager;
    this.skillManager = skillManager;
    this.stateManager = stateManager;
    this.logger = logger;
    this.verificationRunner = new VerificationRunner(workspaceRoot);
    this.githubClient = new GitHubClient();
  }

  private async readSkill(loopName: string): Promise<string> {
    const skillFile = path.join(this.skillManager.getSkillsDir(), `${loopName}.md`);
    try {
      return await fs.readFile(skillFile, 'utf-8');
    } catch {
      const loops = await this.loopManager.loadLoopsInternal();
      return loops[loopName]?.skill_instructions ?? '';
    }
  }

  private async buildBrief(loopName: string, runId: string, branch?: string): Promise<string> {
    const loops = await this.loopManager.loadLoopsInternal();
    const loopConfig = loops[loopName];
    const state = await this.stateManager.loadStateInternal(loopName);
    const skillContent = await this.readSkill(loopName);
    const lessons = state.lessons_learned ?? [];
    const lessonsText = lessons.length
      ? lessons.slice(-10).map((l) => `- ${l}`).join('\n')
      : 'None yet.';
    const branchLine = branch ? `**Branch:** \`${branch}\`\n` : '';

    return `🔄 **Loop run started: ${loopName}** (run_id: \`${runId}\`)

You (the host agent in Cursor/Kiro) execute this loop — no external API keys needed.
Make the code changes in the workspace, then call \`complete_loop_run\` with this run_id.

${branchLine}**Goal:** ${loopConfig.goal}

**Verification command:** \`${loopConfig.verification_command ?? 'none'}\`

---

## Skill Instructions

${skillContent}

---

## Lessons Learned (from previous runs)

${lessonsText}

---

## When done

1. Make all required code changes in the workspace
2. Call \`complete_loop_run\` with:
   - \`loop_name\`: "${loopName}"
   - \`run_id\`: "${runId}"
   - \`summary\`: brief description of what you changed
`;
  }

  private hasGitChanges(): boolean {
    try {
      const output = execSync('git status --porcelain', {
        cwd: this.workspaceRoot,
        encoding: 'utf-8',
        timeout: 30000,
      });
      return output.trim().length > 0;
    } catch {
      return false;
    }
  }

  private createBranch(loopName: string): [boolean, string] {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    const branch = `loop/${loopName}-${timestamp}`;
    try {
      execSync(`git checkout -b ${branch}`, { cwd: this.workspaceRoot, stdio: 'pipe' });
      return [true, branch];
    } catch (error) {
      return [false, String(error)];
    }
  }

  async beginRun(loopName: string, options: { createPr?: boolean } = {}): Promise<string> {
    const createPr = options.createPr ?? true;
    const runId = randomUUID().slice(0, 8);
    await this.logger.info('loop_run_started', loopName, { run_id: runId });

    const loops = await this.loopManager.loadLoopsInternal();
    if (!loops[loopName]) return `❌ Loop '${loopName}' not found.`;

    const state = await this.stateManager.loadStateInternal(loopName);
    if (state.active_run) {
      const active = state.active_run;
      return (
        `⏳ Loop '${loopName}' already has an active run (run_id: \`${active.run_id}\`). ` +
        `Complete it with \`complete_loop_run\` first.`
      );
    }

    let branch: string | undefined;
    if (createPr) {
      const [ok, branchOrErr] = this.createBranch(loopName);
      if (ok) branch = branchOrErr;
      else await this.logger.warning('branch_creation_failed', loopName, { error: branchOrErr });
    }

    await this.stateManager.setActiveRun(loopName, { runId, branch, createPr });
    await this.stateManager.removePendingRun(loopName);

    const brief = await this.buildBrief(loopName, runId, branch);
    await this.logger.info('loop_brief_ready', loopName, { run_id: runId });
    return brief;
  }

  async queueRun(loopName: string): Promise<string> {
    const loops = await this.loopManager.loadLoopsInternal();
    if (!loops[loopName]) return `❌ Loop '${loopName}' not found.`;

    const state = await this.stateManager.loadStateInternal(loopName);
    if (state.active_run) {
      return `⏳ Loop '${loopName}' already has an active run — skipping queue.`;
    }

    const runId = randomUUID().slice(0, 8);
    await this.stateManager.queuePendingRun(loopName, runId, 'schedule');
    await this.logger.info('loop_queued', loopName, { run_id: runId });

    return (
      `📋 Loop '${loopName}' queued (run_id: \`${runId}\`).\n` +
      `Call \`list_pending_runs\` then \`run_loop_now\` when a host agent session is active.`
    );
  }

  async completeRun(
    loopName: string,
    runId: string,
    summary: string,
    options: { createPr?: boolean } = {}
  ): Promise<string> {
    const loops = await this.loopManager.loadLoopsInternal();
    if (!loops[loopName]) return `❌ Loop '${loopName}' not found.`;

    const state = await this.stateManager.loadStateInternal(loopName);
    const active = state.active_run;
    if (!active || active.run_id !== runId) {
      return `❌ No active run with run_id \`${runId}\` for loop '${loopName}'.`;
    }

    const loopConfig = loops[loopName];
    const shouldCreatePr = options.createPr ?? active.create_pr ?? true;
    const branch = active.branch;

    let verificationPassed = false;
    let prResult: PullRequestResult | null = null;
    let status = 'failed';
    let errorMsg: string | undefined;

    try {
      const verification = await this.verificationRunner.run(loopConfig.verification_command ?? '');
      verificationPassed = verification.success;

      if (!verificationPassed) {
        status = 'verification_failed';
        errorMsg = verification.stderr || `Exit code ${verification.exitCode}`;
        await this.stateManager.recordEscalation(loopName, `Verification failed: ${errorMsg}`);
      } else {
        const hasChanges = this.hasGitChanges();
        if (shouldCreatePr && hasChanges && branch) {
          execSync('git add -A', { cwd: this.workspaceRoot, stdio: 'pipe' });
          execSync(`git commit -m "loop(${loopName}): automated changes"`, {
            cwd: this.workspaceRoot,
            stdio: 'pipe',
          });
          const [pushOk, pushMsg] = await this.githubClient.pushBranch(branch, this.workspaceRoot);
          if (pushOk) {
            prResult = await this.githubClient.createPullRequest({
              title: `[loop] ${loopName}: ${loopConfig.description.slice(0, 60)}`,
              body: `Automated loop run.\n\n**Goal:** ${loopConfig.goal}\n\n**Summary:**\n${summary.slice(0, 2000)}`,
              branch,
            });
            status = prResult.success ? 'success' : 'pr_failed';
            if (!prResult.success) errorMsg = prResult.error;
          } else {
            status = 'push_failed';
            errorMsg = pushMsg;
          }
        } else if (hasChanges) {
          status = 'success';
        } else {
          status = 'success_no_changes';
        }
      }
    } catch (error) {
      status = 'error';
      errorMsg = String(error);
      await this.logger.error('loop_run_failed', loopName, { run_id: runId, error: errorMsg });
      await this.stateManager.recordEscalation(loopName, `Run error: ${errorMsg}`);
    }

    const finalSummary = errorMsg ? `${summary} (${status}: ${errorMsg})` : summary;

    await this.stateManager.recordRun(loopName, {
      summary: finalSummary,
      status,
      verificationPassed,
      prUrl: prResult?.success ? prResult.prUrl : undefined,
    });
    await this.stateManager.clearActiveRun(loopName);
    await this.loopManager.updateLastRun(loopName);

    await this.logger.runLog(loopName, runId, {
      status,
      verification_passed: verificationPassed,
      pr_url: prResult?.prUrl ?? null,
      error: errorMsg ?? null,
    });

    const output = [
      `✅ **Loop run complete: ${loopName}** (run_id: ${runId})`,
      `**Status:** ${status}`,
      `**Verification:** ${verificationPassed ? '✅ Passed' : '❌ Failed'}`,
    ];
    if (prResult?.success) output.push(`**PR:** ${prResult.prUrl}`);
    if (errorMsg) output.push(`**Error:** ${errorMsg}`);

    return output.join('\n');
  }

  async run(loopName: string, options: { createPr?: boolean } = {}): Promise<string> {
    return this.beginRun(loopName, options);
  }
}
