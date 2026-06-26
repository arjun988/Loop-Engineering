/**
 * Structured logging for loop engineering
 */

import * as fs from 'fs/promises';
import * as path from 'path';

export class LoopLogger {
  private logsDir: string;

  constructor(logsDir: string) {
    this.logsDir = logsDir;
  }

  private async ensureDir() {
    await fs.mkdir(this.logsDir, { recursive: true });
  }

  private async writeJson(filename: string, entry: Record<string, unknown>) {
    await this.ensureDir();
    const logFile = path.join(this.logsDir, filename);
    await fs.appendFile(logFile, JSON.stringify(entry) + '\n', 'utf-8');
  }

  private entry(
    level: string,
    event: string,
    loopName?: string,
    extra?: Record<string, unknown>
  ): Record<string, unknown> {
    return {
      timestamp: new Date().toISOString(),
      level,
      event,
      loop_name: loopName ?? null,
      ...extra,
    };
  }

  async info(event: string, loopName?: string, extra?: Record<string, unknown>) {
    const entry = this.entry('INFO', event, loopName, extra);
    await this.writeJson('loop-engineering.log', entry);
    console.error(`[${loopName ?? 'system'}] ${event}`);
  }

  async warning(event: string, loopName?: string, extra?: Record<string, unknown>) {
    const entry = this.entry('WARNING', event, loopName, extra);
    await this.writeJson('loop-engineering.log', entry);
    console.error(`[WARN][${loopName ?? 'system'}] ${event}`);
  }

  async error(event: string, loopName?: string, extra?: Record<string, unknown>) {
    const entry = this.entry('ERROR', event, loopName, extra);
    await this.writeJson('loop-engineering.log', entry);
    console.error(`[ERROR][${loopName ?? 'system'}] ${event}`);
  }

  async runLog(loopName: string, runId: string, data: Record<string, unknown>) {
    const entry = this.entry('INFO', 'loop_run', loopName, { run_id: runId, ...data });
    await this.writeJson(`${loopName}-runs.log`, entry);
  }
}
