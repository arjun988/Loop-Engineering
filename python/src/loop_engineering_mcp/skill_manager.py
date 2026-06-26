"""Skill template management."""

from datetime import datetime
from pathlib import Path
from typing import Optional
import aiofiles


class SkillManager:
    """Manages skill templates for loops."""
    
    def __init__(self, skills_dir: Path):
        """Initialize the skill manager."""
        self.skills_dir = skills_dir
        self.skills_dir.mkdir(parents=True, exist_ok=True)
    
    async def create_skill(
        self,
        name: str,
        description: str,
        instructions: str,
        project_context: Optional[dict] = None
    ) -> str:
        """Create a new skill template."""
        skill_file = self.skills_dir / f"{name}.md"
        
        if skill_file.exists():
            return f"⚠️ Skill '{name}' already exists. Updating..."
        
        # Build skill content
        content = [
            "---",
            f"name: {name}",
            f"description: {description}",
            f"created: {datetime.now().isoformat()}",
            "---\n",
            f"# {name.replace('-', ' ').title()} Skill\n",
            "## Task",
            instructions,
            ""
        ]
        
        if project_context:
            content.append("\n## Project Context")
            if "test_framework" in project_context:
                content.append(f"- Test framework: {project_context['test_framework']}")
            if "ci_platform" in project_context:
                content.append(f"- CI platform: {project_context['ci_platform']}")
            if "forbidden_paths" in project_context:
                content.append(f"- Never modify: {', '.join(project_context['forbidden_paths'])}")
            content.append("")
        
        content.extend([
            "\n## Success Criteria",
            "- Task completed as described",
            "- Verification passes",
            "- State updated",
            ""
        ])
        
        async with aiofiles.open(skill_file, 'w') as f:
            await f.write("\n".join(content))
        
        return f"""✅ Skill '{name}' created!

**Location:** .loop/skills/{name}.md

You can edit this file to:
- Add more detailed instructions
- Include project-specific patterns
- Add examples of good/bad outputs
- Document lessons learned"""
    
    async def list_skills(self) -> str:
        """List all available skills."""
        skills = list(self.skills_dir.glob("*.md"))
        
        if not skills:
            return """📚 No skills created yet.

Skills are reusable templates that contain:
- Instructions for the AI agent
- Project context
- Success criteria
- Lessons learned

Create a skill with: add_skill()"""
        
        output = ["📚 **Available Skills**\n"]
        
        for skill_file in sorted(skills):
            name = skill_file.stem
            async with aiofiles.open(skill_file, 'r') as f:
                content = await f.read()
                # Extract description from frontmatter
                lines = content.split('\n')
                description = "No description"
                for line in lines[1:10]:  # Check first few lines
                    if line.startswith("description:"):
                        description = line.replace("description:", "").strip()
                        break
            
            output.append(f"**{name}**")
            output.append(f"  {description}")
            output.append(f"  File: .loop/skills/{name}.md\n")
        
        return "\n".join(output)
    
    async def delete_skill(self, name: str) -> str:
        """Delete a skill template."""
        skill_file = self.skills_dir / f"{name}.md"
        
        if not skill_file.exists():
            return f"⚠️ Skill '{name}' not found (already deleted or never existed)"
        
        skill_file.unlink()
        return f"✅ Skill '{name}' deleted"
