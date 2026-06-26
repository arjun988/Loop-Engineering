/**
 * State tracking and metrics for loops
 */

import * as fs from 'fs/promises';
import * as path from 'path';

interface LoopState {
  loop_name: string;
  created_at: string;
  last_run?: string;
  status: string;
  runs: any[];
  metrics: {
    total_runs: number;
    prs_opened: number;
    prs_merged: number;
    acceptance_rate: number;
    total_token_cost: number;
  };
  lessons_learned: string[];
  escalations: any[];
  pending_runs: Array<{ run_id: string; queued_at: string; source: string }>;
  active_run: {
    run_id: string;
    started_at: string;
    branch?: string;
    create_pr: boolean;
  } | null;
}

export class StateManager {
  private stateDir: string;

  constructor(stateDir: string) {
    this.stateDir = stateDir;
    this.ensureDir();
  }

  private async ensureDir() {
    await fs.mkdir(this.stateDir, { recursive: true });
  }

  async initializeState(loopName: string): Promise<string> {
    const stateFile = path.join(this.stateDir, `${loopName}.json`);

    const initialState: LoopState = {
      loop_name: loopName,
      created_at: new Date().toISOString(),
      status: 'initialized',
      runs: [],
      metrics: {
        total_runs: 0,
        prs_opened: 0,
        prs_merged: 0,
        acceptance_rate: 0.0,
        total_token_cost: 0.0,
      },
      lessons_learned: [],
      escalations: [],
      pending_runs: [],
      active_run: null,
    };

    await fs.writeFile(stateFile, JSON.stringify(initialState, null, 2));
    return `✅ State initialized for '${loopName}'`;
  }

  private async loadState(loopName: string): Promise<LoopState> {
    const stateFile = path.join(this.stateDir, `${loopName}.json`);
    
    try {
      const content = await fs.readFile(stateFile, 'utf-8');
      return JSON.parse(content);
    } catch {
      // Initialize if doesn't exist
      await this.initializeState(loopName);
      const content = await fs.readFile(stateFile, 'utf-8');
      return JSON.parse(content);
    }
  }

  private async saveState(loopName: string, state: LoopState) {
    const stateFile = path.join(this.stateDir, `${loopName}.json`);
    await fs.writeFile(stateFile, JSON.stringify(state, null, 2));
  }

  async loadStateInternal(loopName: string): Promise<LoopState> {
    return this.loadState(loopName);
  }

  async recordRun(
    loopName: string,
    options: {
      summary: string;
      status: string;
      tokenCost?: number;
      verificationPassed?: boolean;
      prUrl?: string;
    }
  ): Promise<void> {
    const state = await this.loadState(loopName);
    const timestamp = new Date().toISOString();

    state.runs.push({
      timestamp,
      summary: options.summary,
      status: options.status,
      verification_passed: options.verificationPassed ?? false,
      pr_url: options.prUrl,
    });
    state.last_run = timestamp;
    state.status = options.status;

    state.metrics.total_runs += 1;
    state.metrics.total_token_cost += options.tokenCost ?? 0;

    if (options.prUrl) {
      state.metrics.prs_opened += 1;
      const opened = state.metrics.prs_opened;
      const merged = state.metrics.prs_merged;
      state.metrics.acceptance_rate = opened > 0 ? merged / opened : 0;
    }

    await this.saveState(loopName, state);
  }

  async recordEscalation(loopName: string, reason: string): Promise<void> {
    const state = await this.loadState(loopName);
    state.escalations.push({ timestamp: new Date().toISOString(), reason });
    state.status = 'escalated';
    await this.saveState(loopName, state);
  }

  async queuePendingRun(loopName: string, runId: string, source = 'schedule'): Promise<void> {
    const state = await this.loadState(loopName);
    if (!state.pending_runs.some((p) => p.run_id === runId)) {
      state.pending_runs.push({
        run_id: runId,
        queued_at: new Date().toISOString(),
        source,
      });
    }
    await this.saveState(loopName, state);
  }

  async removePendingRun(loopName: string): Promise<void> {
    const state = await this.loadState(loopName);
    state.pending_runs = [];
    await this.saveState(loopName, state);
  }

  async setActiveRun(
    loopName: string,
    options: { runId: string; branch?: string; createPr: boolean }
  ): Promise<void> {
    const state = await this.loadState(loopName);
    state.active_run = {
      run_id: options.runId,
      started_at: new Date().toISOString(),
      branch: options.branch,
      create_pr: options.createPr,
    };
    state.status = 'running';
    await this.saveState(loopName, state);
  }

  async clearActiveRun(loopName: string): Promise<void> {
    const state = await this.loadState(loopName);
    state.active_run = null;
    await this.saveState(loopName, state);
  }

  async listPendingRuns(): Promise<string> {
    try {
      const files = await fs.readdir(this.stateDir);
      const pendingItems: Array<[string, { run_id: string; queued_at?: string; source?: string }]> = [];

      for (const file of files.filter((f) => f.endsWith('.json'))) {
        const content = await fs.readFile(path.join(this.stateDir, file), 'utf-8');
        const state: LoopState = JSON.parse(content);
        const loopName = state.loop_name || path.basename(file, '.json');
        for (const item of state.pending_runs ?? []) {
          pendingItems.push([loopName, item]);
        }
        if (state.active_run && !(state.pending_runs?.length)) {
          pendingItems.push([
            loopName,
            {
              run_id: state.active_run.run_id,
              queued_at: state.active_run.started_at,
              source: 'active',
            },
          ]);
        }
      }

      if (pendingItems.length === 0) {
        return (
          '📋 **No pending loop runs**\n\n' +
          'Scheduled loops are queued here until a host agent (Cursor/Kiro) ' +
          'calls `run_loop_now` to begin execution.'
        );
      }

      const output = ['📋 **Pending Loop Runs**\n'];
      for (const [loopName, item] of pendingItems) {
        output.push(`- **${loopName}** (run_id: \`${item.run_id}\`)`);
        output.push(`  Source: ${item.source ?? 'unknown'}`);
        output.push(`  Queued: ${item.queued_at ?? 'unknown'}\n`);
      }
      output.push('Call `run_loop_now("<name>")` to begin execution in this session.');
      return output.join('\n');
    } catch (error) {
      return `❌ Error listing pending runs: ${error}`;
    }
  }

  async getState(loopName: string): Promise<string> {
    try {
      const state = await this.loadState(loopName);
      const metrics = state.metrics;
      const runs = state.runs;
      const lessons = state.lessons_learned;
      const escalations = state.escalations;

      const output: string[] = [
        `📊 **State for loop: ${loopName}**\n`,
        `**Last Run:** ${state.last_run || 'Never'}`,
        `**Status:** ${state.status}\n`,
        '**Metrics:**',
        `- Total runs: ${metrics.total_runs}`,
        `- PRs opened: ${metrics.prs_opened}`,
        `- PRs merged: ${metrics.prs_merged}`,
        `- Acceptance rate: ${(metrics.acceptance_rate * 100).toFixed(1)}%`,
        `- Token cost: $${metrics.total_token_cost.toFixed(2)}\n`,
      ];

      if (runs.length > 0) {
        output.push('**Recent Runs (last 5):**');
        runs.slice(-5).forEach((run) => {
          output.push(`- ${run.timestamp || 'Unknown'}: ${run.summary || 'No summary'}`);
        });
        output.push('');
      }

      if (lessons.length > 0) {
        output.push('**Lessons Learned:**');
        lessons.slice(-5).forEach((lesson) => {
          output.push(`- ${lesson}`);
        });
        output.push('');
      }

      if (escalations.length > 0) {
        output.push('**Recent Escalations:**');
        escalations.slice(-3).forEach((escalation) => {
          output.push(`- ${escalation.timestamp || 'Unknown'}: ${escalation.reason || 'No reason'}`);
        });
      }

      return output.join('\n');
    } catch (error) {
      return `❌ Error loading state for '${loopName}': ${error}`;
    }
  }

  async addLesson(loopName: string, lesson: string): Promise<string> {
    const state = await this.loadState(loopName);

    const timestamp = new Date().toISOString();
    const lessonEntry = `[${timestamp}] ${lesson}`;

    state.lessons_learned.push(lessonEntry);
    await this.saveState(loopName, state);

    return `✅ Lesson added to '${loopName}'

**Lesson:** ${lesson}

This will be included in future loop runs to avoid repeating mistakes.`;
  }

  async deleteState(loopName: string): Promise<string> {
    const stateFile = path.join(this.stateDir, `${loopName}.json`);

    try {
      await fs.unlink(stateFile);
      return `✅ State for '${loopName}' deleted`;
    } catch {
      return `⚠️ State for '${loopName}' not found (already deleted)`;
    }
  }

  async getMetrics(): Promise<string> {
    try {
      const files = await fs.readdir(this.stateDir);
      const stateFiles = files.filter((f) => f.endsWith('.json'));

      if (stateFiles.length === 0) {
        return `📊 **No loops with metrics yet**

Metrics will appear here once loops start running:
- Total runs
- PRs opened/merged
- Acceptance rates
- Token costs
- Time saved estimates`;
      }

      let totalRuns = 0;
      let totalPrsOpened = 0;
      let totalPrsMerged = 0;
      let totalTokenCost = 0.0;
      const loopMetrics: any[] = [];

      for (const stateFile of stateFiles) {
        const content = await fs.readFile(path.join(this.stateDir, stateFile), 'utf-8');
        const state: LoopState = JSON.parse(content);
        const metrics = state.metrics;

        const loopName = state.loop_name || path.basename(stateFile, '.json');
        totalRuns += metrics.total_runs;
        totalPrsOpened += metrics.prs_opened;
        totalPrsMerged += metrics.prs_merged;
        totalTokenCost += metrics.total_token_cost;

        loopMetrics.push({
          name: loopName,
          runs: metrics.total_runs,
          acceptance_rate: metrics.acceptance_rate,
        });
      }

      const overallAcceptance =
        totalPrsOpened > 0 ? (totalPrsMerged / totalPrsOpened) * 100 : 0;

      // Estimate time saved (assume 30 min per PR)
      const timeSavedHours = totalPrsMerged * 0.5;

      const output: string[] = [
        '📊 **Overall Loop Metrics**\n',
        '**Summary:**',
        `- Total runs: ${totalRuns}`,
        `- PRs opened: ${totalPrsOpened}`,
        `- PRs merged: ${totalPrsMerged}`,
        `- Overall acceptance rate: ${overallAcceptance.toFixed(1)}%`,
        `- Total token cost: $${totalTokenCost.toFixed(2)}`,
        `- Estimated time saved: ~${timeSavedHours.toFixed(1)} hours\n`,
        '**Per Loop:**',
      ];

      loopMetrics
        .sort((a, b) => b.runs - a.runs)
        .forEach((loop) => {
          output.push(
            `- ${loop.name}: ${loop.runs} runs, ${(loop.acceptance_rate * 100).toFixed(1)}% acceptance`
          );
        });

      if (overallAcceptance >= 50) {
        output.push('\n✅ **Status:** Healthy (acceptance rate >50%)');
      } else {
        output.push('\n⚠️ **Warning:** Acceptance rate below 50% - loops may need adjustment');
      }

      return output.join('\n');
    } catch (error) {
      return `❌ Error getting metrics: ${error}`;
    }
  }
}
