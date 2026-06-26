import * as fs from 'fs/promises';
import * as os from 'os';
import * as path from 'path';
import { LoopLogger } from '../src/logger.js';

describe('LoopLogger', () => {
  let tmpDir: string;
  let logger: LoopLogger;

  beforeEach(async () => {
    tmpDir = await fs.mkdtemp(path.join(os.tmpdir(), 'loop-log-'));
    logger = new LoopLogger(tmpDir);
  });

  afterEach(async () => {
    await fs.rm(tmpDir, { recursive: true, force: true });
  });

  it('writes structured log entries', async () => {
    await logger.info('test_event', 'my-loop', { detail: 'value' });
    const content = await fs.readFile(path.join(tmpDir, 'loop-engineering.log'), 'utf-8');
    const entry = JSON.parse(content.trim().split('\n').pop()!);
    expect(entry.event).toBe('test_event');
    expect(entry.loop_name).toBe('my-loop');
    expect(entry.detail).toBe('value');
  });

  it('writes run logs', async () => {
    await logger.runLog('ci-triage', 'abc123', { status: 'success' });
    const content = await fs.readFile(path.join(tmpDir, 'ci-triage-runs.log'), 'utf-8');
    const entry = JSON.parse(content.trim());
    expect(entry.run_id).toBe('abc123');
    expect(entry.status).toBe('success');
  });
});
