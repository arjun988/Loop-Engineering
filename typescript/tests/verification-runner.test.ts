import * as fs from 'fs/promises';
import * as os from 'os';
import * as path from 'path';
import { VerificationRunner } from '../src/verification-runner.js';

describe('VerificationRunner', () => {
  let tmpDir: string;
  let runner: VerificationRunner;

  beforeEach(async () => {
    tmpDir = await fs.mkdtemp(path.join(os.tmpdir(), 'loop-test-'));
    runner = new VerificationRunner(tmpDir, 10);
  });

  afterEach(async () => {
    await fs.rm(tmpDir, { recursive: true, force: true });
  });

  it('skips when no verification configured', async () => {
    const result = await runner.run("echo 'No verification configured'");
    expect(result.success).toBe(true);
    expect(result.stdout.toLowerCase()).toContain('skipped');
  });

  it('runs successful command', async () => {
    const cmd = process.platform === 'win32' ? 'echo hello' : 'echo hello';
    const result = await runner.run(cmd, { cwd: tmpDir });
    expect(result.success).toBe(true);
    expect(result.stdout).toContain('hello');
  });

  it('handles failed command', async () => {
    const cmd = process.platform === 'win32' ? 'exit 1' : 'exit 1';
    const result = await runner.run(cmd, { cwd: tmpDir });
    expect(result.success).toBe(false);
  });
});
