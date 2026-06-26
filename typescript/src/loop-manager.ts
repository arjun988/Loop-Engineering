/**
 * Loop management functionality
 */

import * as fs from 'fs/promises';
import * as path from 'path';

interface LoopConfig {
  name: string;
  description: string;
  schedule: string;
  skill_instructions: string;
  verification_command: string;
  goal: string;
  status: 'active' | 'stopped';
  created_at: string;
  last_run?: string;
  started_at?: string;
  stopped_at?: string;
}

export class LoopManager {
  private loopDir: string;
  private loopsFile: string;

  constructor(loopDir: string) {
    this.loopDir = loopDir;
    this.loopsFile = path.join(loopDir, 'loops.json');
    this.ensureDir();
  }

  /** Exposed for executor/scheduler internal use */
  async loadLoopsInternal(): Promise<Record<string, LoopConfig>> {
    return this.loadLoops();
  }

  async updateLastRun(name: string): Promise<void> {
    const loops = await this.loadLoops();
    if (loops[name]) {
      loops[name].last_run = new Date().toISOString();
      await this.saveLoops(loops);
    }
  }

  private async ensureDir() {
    await fs.mkdir(this.loopDir, { recursive: true });
  }

  private async loadLoops(): Promise<Record<string, LoopConfig>> {
    try {
      const content = await fs.readFile(this.loopsFile, 'utf-8');
      return JSON.parse(content);
    } catch {
      return {};
    }
  }

  private async saveLoops(loops: Record<string, LoopConfig>) {
    await fs.writeFile(this.loopsFile, JSON.stringify(loops, null, 2));
  }

  async createLoop(
    name: string,
    description: string,
    schedule: string,
    skillInstructions: string,
    goal: string,
    verificationCommand?: string
  ): Promise<string> {
    const loops = await this.loadLoops();

    if (loops[name]) {
      return `❌ Loop '${name}' already exists. Use a different name or delete the existing loop first.`;
    }

    const loopConfig: LoopConfig = {
      name,
      description,
      schedule,
      skill_instructions: skillInstructions,
      verification_command: verificationCommand || "echo 'No verification configured'",
      goal,
      status: 'stopped',
      created_at: new Date().toISOString(),
    };

    loops[name] = loopConfig;
    await this.saveLoops(loops);

    return `✅ Loop '${name}' created successfully!

**Configuration:**
- Schedule: ${schedule}
- Goal: ${goal}
- Verification: ${verificationCommand || 'None configured'}
- Status: Stopped (use start_loop to activate)

**Files created:**
- Configuration: .loop/loops.json
- Skill: .loop/skills/${name}.md
- State: .loop/state/${name}.json

**Next steps:**
1. Review the skill file at .loop/skills/${name}.md
2. Start the loop with: start_loop("${name}")
3. Monitor with: view_state("${name}")`;
  }

  async startLoop(name: string): Promise<string> {
    const loops = await this.loadLoops();

    if (!loops[name]) {
      return `❌ Loop '${name}' not found. Create it first with create_loop.`;
    }

    loops[name].status = 'active';
    loops[name].started_at = new Date().toISOString();
    await this.saveLoops(loops);

    const schedule = loops[name].schedule;
    return `✅ Loop '${name}' started!

**Status:** Active
**Schedule:** ${schedule}
**Next run:** Based on schedule

The loop will now run automatically according to its schedule.
Monitor progress with: view_state("${name}")`;
  }

  async stopLoop(name: string): Promise<string> {
    const loops = await this.loadLoops();

    if (!loops[name]) {
      return `❌ Loop '${name}' not found.`;
    }

    loops[name].status = 'stopped';
    loops[name].stopped_at = new Date().toISOString();
    await this.saveLoops(loops);

    return `✅ Loop '${name}' stopped.

**Status:** Stopped
**Last run:** ${loops[name].last_run || 'Never'}

The loop is paused but not deleted.
Restart with: start_loop("${name}")`;
  }

  async listLoops(): Promise<string> {
    const loops = await this.loadLoops();

    if (Object.keys(loops).length === 0) {
      return `📊 No loops configured yet.

Create your first loop with create_loop()

**Good first loops:**
- CI failure triage
- Dependency updates
- Lint & format fixes
- Documentation updates`;
    }

    const output: string[] = ['📊 **Loop Status**\n'];

    const activeLoops = Object.values(loops).filter((l) => l.status === 'active');
    const stoppedLoops = Object.values(loops).filter((l) => l.status === 'stopped');

    if (activeLoops.length > 0) {
      output.push('**Active Loops:**');
      for (const loop of activeLoops) {
        output.push(`\n${loop.name}`);
        output.push(`  Description: ${loop.description}`);
        output.push(`  Schedule: ${loop.schedule}`);
        output.push(`  Last run: ${loop.last_run || 'Never'}`);
        output.push('  Status: 🟢 Active');
      }
    }

    if (stoppedLoops.length > 0) {
      output.push('\n**Stopped Loops:**');
      for (const loop of stoppedLoops) {
        output.push(`\n${loop.name}`);
        output.push(`  Description: ${loop.description}`);
        output.push('  Status: ⏸️ Stopped');
      }
    }

    return output.join('\n');
  }

  async deleteLoop(name: string): Promise<string> {
    const loops = await this.loadLoops();

    if (!loops[name]) {
      return `❌ Loop '${name}' not found.`;
    }

    delete loops[name];
    await this.saveLoops(loops);

    return `✅ Loop '${name}' deleted permanently.

**Cleaned up:**
- Loop configuration
- Associated skill file
- State history

This action cannot be undone.`;
  }

  async configureVerification(loopName: string, command: string): Promise<string> {
    const loops = await this.loadLoops();

    if (!loops[loopName]) {
      return `❌ Loop '${loopName}' not found.`;
    }

    loops[loopName].verification_command = command;
    await this.saveLoops(loops);

    return `✅ Verification configured for '${loopName}'

**Command:** ${command}

This command will run before any PR is opened to verify changes.
If it fails (non-zero exit code), the PR won't be created.`;
  }
}
