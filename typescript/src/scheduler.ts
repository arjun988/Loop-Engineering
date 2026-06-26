/**
 * Cron-like scheduler for active loops
 */

import cronParser from 'cron-parser';
import { LoopLogger } from './logger.js';
import { LoopManager } from './loop-manager.js';

export class LoopScheduler {
  private loopManager: LoopManager;
  private logger: LoopLogger;
  private runCallback: (loopName: string, options?: Record<string, unknown>) => Promise<string>;
  private pollInterval: number;
  private running = false;
  private intervalId: ReturnType<typeof setInterval> | null = null;
  private lastRun: Map<string, Date> = new Map();
  private inProgress: Set<string> = new Set();

  constructor(
    loopManager: LoopManager,
    logger: LoopLogger,
    runCallback: (loopName: string, options?: Record<string, unknown>) => Promise<string>,
    pollInterval = 60
  ) {
    this.loopManager = loopManager;
    this.logger = logger;
    this.runCallback = runCallback;
    this.pollInterval = pollInterval;
  }

  private isDue(schedule: string, loopName: string): boolean {
    try {
      const interval = cronParser.parseExpression(schedule);
      const prevRun = interval.prev().toDate();
      const last = this.lastRun.get(loopName);
      if (!last || prevRun > last) return true;
      return false;
    } catch (error) {
      this.logger.warning('invalid_cron', loopName, { schedule, error: String(error) });
      return false;
    }
  }

  private async tick() {
    const loops = await this.loopManager.loadLoopsInternal();
    for (const [name, config] of Object.entries(loops)) {
      if (config.status !== 'active') continue;
      if (this.inProgress.has(name)) continue;
      if (!this.isDue(config.schedule, name)) continue;

      this.inProgress.add(name);
      try {
        await this.logger.info('scheduler_triggered', name, { schedule: config.schedule });
        await this.runCallback(name);
        this.lastRun.set(name, new Date());
      } catch (error) {
        await this.logger.error('scheduler_run_failed', name, { error: String(error) });
      } finally {
        this.inProgress.delete(name);
      }
    }
  }

  start() {
    if (this.intervalId) return;
    this.running = true;
    this.logger.info('scheduler_started', undefined, { poll_interval: this.pollInterval });
    this.intervalId = setInterval(() => {
      this.tick().catch((err) =>
        this.logger.error('scheduler_tick_failed', undefined, { error: String(err) })
      );
    }, this.pollInterval * 1000);
  }

  async stop() {
    this.running = false;
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
    await this.logger.info('scheduler_stopped');
  }

  async runNow(loopName: string, options?: Record<string, unknown>): Promise<string> {
    if (this.inProgress.has(loopName)) {
      return `⏳ Loop '${loopName}' is already running.`;
    }
    this.inProgress.add(loopName);
    try {
      const result = await this.runCallback(loopName, options);
      this.lastRun.set(loopName, new Date());
      return result;
    } finally {
      this.inProgress.delete(loopName);
    }
  }
}
