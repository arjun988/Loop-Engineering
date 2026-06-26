import * as fs from 'fs/promises';
import * as os from 'os';
import * as path from 'path';
import { StateManager } from '../src/state-manager.js';

describe('StateManager', () => {
  let tmpDir: string;
  let stateManager: StateManager;

  beforeEach(async () => {
    tmpDir = await fs.mkdtemp(path.join(os.tmpdir(), 'loop-state-'));
    stateManager = new StateManager(path.join(tmpDir, 'state'));
  });

  afterEach(async () => {
    await fs.rm(tmpDir, { recursive: true, force: true });
  });

  it('initializes state', async () => {
    const result = await stateManager.initializeState('test-loop');
    expect(result).toContain('initialized');
    const state = await stateManager.loadStateInternal('test-loop');
    expect(state.metrics.total_runs).toBe(0);
  });

  it('records runs and updates metrics', async () => {
    await stateManager.initializeState('test-loop');
    await stateManager.recordRun('test-loop', {
      summary: 'Test run',
      status: 'success',
      tokenCost: 0.05,
      verificationPassed: true,
      prUrl: 'https://github.com/org/repo/pull/1',
    });
    const state = await stateManager.loadStateInternal('test-loop');
    expect(state.metrics.total_runs).toBe(1);
    expect(state.metrics.prs_opened).toBe(1);
    expect(state.runs).toHaveLength(1);
  });

  it('records escalations', async () => {
    await stateManager.initializeState('test-loop');
    await stateManager.recordEscalation('test-loop', 'Verification failed');
    const state = await stateManager.loadStateInternal('test-loop');
    expect(state.escalations).toHaveLength(1);
    expect(state.status).toBe('escalated');
  });
});
