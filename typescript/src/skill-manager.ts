/**
 * Skill template management
 */

import * as fs from 'fs/promises';
import * as path from 'path';

export class SkillManager {
  private skillsDir: string;

  constructor(skillsDir: string) {
    this.skillsDir = skillsDir;
    this.ensureDir();
  }

  getSkillsDir(): string {
    return this.skillsDir;
  }

  private async ensureDir() {
    await fs.mkdir(this.skillsDir, { recursive: true });
  }

  async createSkill(
    name: string,
    description: string,
    instructions: string,
    projectContext?: any
  ): Promise<string> {
    const skillFile = path.join(this.skillsDir, `${name}.md`);

    const content = [
      '---',
      `name: ${name}`,
      `description: ${description}`,
      `created: ${new Date().toISOString()}`,
      '---\n',
      `# ${name.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase())} Skill\n`,
      '## Task',
      instructions,
      '',
    ];

    if (projectContext) {
      content.push('\n## Project Context');
      if (projectContext.test_framework) {
        content.push(`- Test framework: ${projectContext.test_framework}`);
      }
      if (projectContext.ci_platform) {
        content.push(`- CI platform: ${projectContext.ci_platform}`);
      }
      if (projectContext.forbidden_paths) {
        content.push(`- Never modify: ${projectContext.forbidden_paths.join(', ')}`);
      }
      content.push('');
    }

    content.push(
      '\n## Success Criteria',
      '- Task completed as described',
      '- Verification passes',
      '- State updated',
      ''
    );

    await fs.writeFile(skillFile, content.join('\n'));

    return `✅ Skill '${name}' created!

**Location:** .loop/skills/${name}.md

You can edit this file to:
- Add more detailed instructions
- Include project-specific patterns
- Add examples of good/bad outputs
- Document lessons learned`;
  }

  async listSkills(): Promise<string> {
    try {
      const files = await fs.readdir(this.skillsDir);
      const skills = files.filter((f) => f.endsWith('.md'));

      if (skills.length === 0) {
        return `📚 No skills created yet.

Skills are reusable templates that contain:
- Instructions for the AI agent
- Project context
- Success criteria
- Lessons learned

Create a skill with: add_skill()`;
      }

      const output: string[] = ['📚 **Available Skills**\n'];

      for (const skillFile of skills.sort()) {
        const name = path.basename(skillFile, '.md');
        const content = await fs.readFile(path.join(this.skillsDir, skillFile), 'utf-8');
        
        // Extract description from frontmatter
        let description = 'No description';
        const lines = content.split('\n');
        for (let i = 1; i < Math.min(10, lines.length); i++) {
          if (lines[i].startsWith('description:')) {
            description = lines[i].replace('description:', '').trim();
            break;
          }
        }

        output.push(`**${name}**`);
        output.push(`  ${description}`);
        output.push(`  File: .loop/skills/${name}.md\n`);
      }

      return output.join('\n');
    } catch (error) {
      return '📚 No skills directory found';
    }
  }

  async deleteSkill(name: string): Promise<string> {
    const skillFile = path.join(this.skillsDir, `${name}.md`);

    try {
      await fs.unlink(skillFile);
      return `✅ Skill '${name}' deleted`;
    } catch {
      return `⚠️ Skill '${name}' not found (already deleted or never existed)`;
    }
  }
}
