#!/usr/bin/env node
/**
 * Standalone worker entry point for loop scheduler
 */

import * as path from 'path';
import { LoopManager } from './loop-manager.js';
import { SkillManager } from './skill-manager.js';
import { StateManager } from './state-manager.js';
import { LoopLogger } from './logger.js';
import { LoopExecutor } from './loop-executor.js';
import { LoopScheduler } from './scheduler.js';

async function main() {
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
  const scheduler = new LoopScheduler(loopManager, logger, (name) => executor.queueRun(name));

  await logger.info('worker_started', undefined, { workspace: workspaceRoot });
  scheduler.start();

  process.on('SIGINT', async () => {
    await scheduler.stop();
    await logger.info('worker_stopped');
    process.exit(0);
  });
}

main().catch((err) => {
  console.error('Worker error:', err);
  process.exit(1);
});
