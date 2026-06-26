/**
 * Execute verification commands with timeout and error handling
 */

import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

export interface VerificationResult {
  success: boolean;
  exitCode: number;
  stdout: string;
  stderr: string;
  timedOut: boolean;
  durationSeconds: number;
  error?: string;
}

export class VerificationRunner {
  private workspaceRoot: string;
  private defaultTimeout: number;

  constructor(workspaceRoot: string, defaultTimeout = 600) {
    this.workspaceRoot = workspaceRoot;
    this.defaultTimeout = defaultTimeout;
  }

  async run(
    command: string,
    options: { timeout?: number; cwd?: string } = {}
  ): Promise<VerificationResult> {
    if (!command || command.trim() === "echo 'No verification configured'") {
      return {
        success: true,
        exitCode: 0,
        stdout: 'No verification configured — skipped',
        stderr: '',
        timedOut: false,
        durationSeconds: 0,
      };
    }

    const cwd = options.cwd ?? this.workspaceRoot;
    const timeoutMs = (options.timeout ?? this.defaultTimeout) * 1000;
    const start = Date.now();

    try {
      const { stdout, stderr } = await execAsync(command, {
        cwd,
        timeout: timeoutMs,
        maxBuffer: 10 * 1024 * 1024,
        shell: process.platform === 'win32' ? 'cmd.exe' : '/bin/sh',
      });
      const duration = (Date.now() - start) / 1000;
      return {
        success: true,
        exitCode: 0,
        stdout,
        stderr,
        timedOut: false,
        durationSeconds: duration,
      };
    } catch (error: unknown) {
      const duration = (Date.now() - start) / 1000;
      const execError = error as { code?: number; killed?: boolean; stdout?: string; stderr?: string; message?: string };
      if (execError.killed) {
        return {
          success: false,
          exitCode: -1,
          stdout: execError.stdout ?? '',
          stderr: `Verification timed out after ${timeoutMs / 1000}s`,
          timedOut: true,
          durationSeconds: duration,
          error: 'timeout',
        };
      }
      return {
        success: false,
        exitCode: execError.code ?? -1,
        stdout: execError.stdout ?? '',
        stderr: execError.stderr ?? execError.message ?? String(error),
        timedOut: false,
        durationSeconds: duration,
        error: execError.message,
      };
    }
  }
}
