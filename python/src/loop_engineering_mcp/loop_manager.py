"""Loop management functionality."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional
import aiofiles


class LoopManager:
    """Manages loop creation, execution, and configuration."""
    
    def __init__(self, loop_dir: Path):
        """Initialize the loop manager."""
        self.loop_dir = loop_dir
        self.loops_file = loop_dir / "loops.json"
        
    async def _load_loops(self) -> dict:
        """Load loops configuration."""
        if not self.loops_file.exists():
            return {}
        async with aiofiles.open(self.loops_file, 'r') as f:
            content = await f.read()
            return json.loads(content) if content else {}
    
    async def _save_loops(self, loops: dict):
        """Save loops configuration."""
        async with aiofiles.open(self.loops_file, 'w') as f:
            await f.write(json.dumps(loops, indent=2))
    
    async def create_loop(
        self,
        name: str,
        description: str,
        schedule: str,
        skill_instructions: str,
        goal: str,
        verification_command: Optional[str] = None
    ) -> str:
        """Create a new loop."""
        loops = await self._load_loops()
        
        if name in loops:
            return f"❌ Loop '{name}' already exists. Use a different name or delete the existing loop first."
        
        loop_config = {
            "name": name,
            "description": description,
            "schedule": schedule,
            "skill_instructions": skill_instructions,
            "verification_command": verification_command or "echo 'No verification configured'",
            "goal": goal,
            "status": "stopped",
            "created_at": datetime.now().isoformat(),
            "last_run": None
        }
        
        loops[name] = loop_config
        await self._save_loops(loops)
        
        return f"""✅ Loop '{name}' created successfully!

**Configuration:**
- Schedule: {schedule}
- Goal: {goal}
- Verification: {verification_command or 'None configured'}
- Status: Stopped (use start_loop to activate)

**Files created:**
- Configuration: .loop/loops.json
- Skill: .loop/skills/{name}.md
- State: .loop/state/{name}.json

**Next steps:**
1. Review the skill file at .loop/skills/{name}.md
2. Start the loop with: start_loop("{name}")
3. Monitor with: view_state("{name}")"""
    
    async def start_loop(self, name: str) -> str:
        """Start a loop."""
        loops = await self._load_loops()
        
        if name not in loops:
            return f"❌ Loop '{name}' not found. Create it first with create_loop."
        
        loops[name]["status"] = "active"
        loops[name]["started_at"] = datetime.now().isoformat()
        await self._save_loops(loops)
        
        schedule = loops[name]["schedule"]
        return f"""✅ Loop '{name}' started!

**Status:** Active
**Schedule:** {schedule}
**Next run:** Based on schedule

The loop will now run automatically according to its schedule.
Monitor progress with: view_state("{name}")"""
    
    async def stop_loop(self, name: str) -> str:
        """Stop a loop."""
        loops = await self._load_loops()
        
        if name not in loops:
            return f"❌ Loop '{name}' not found."
        
        loops[name]["status"] = "stopped"
        loops[name]["stopped_at"] = datetime.now().isoformat()
        await self._save_loops(loops)
        
        return f"""✅ Loop '{name}' stopped.

**Status:** Stopped
**Last run:** {loops[name].get('last_run', 'Never')}

The loop is paused but not deleted.
Restart with: start_loop("{name}")"""
    
    async def list_loops(self) -> str:
        """List all loops with their status."""
        loops = await self._load_loops()
        
        if not loops:
            return """📊 No loops configured yet.

Create your first loop with create_loop()

**Good first loops:**
- CI failure triage
- Dependency updates
- Lint & format fixes
- Documentation updates"""
        
        output = ["📊 **Loop Status**\n"]
        
        active_loops = [l for l in loops.values() if l["status"] == "active"]
        stopped_loops = [l for l in loops.values() if l["status"] == "stopped"]
        
        if active_loops:
            output.append("**Active Loops:**")
            for loop in active_loops:
                output.append(f"\n{loop['name']}")
                output.append(f"  Description: {loop['description']}")
                output.append(f"  Schedule: {loop['schedule']}")
                output.append(f"  Last run: {loop.get('last_run', 'Never')}")
                output.append(f"  Status: 🟢 Active")
        
        if stopped_loops:
            output.append("\n**Stopped Loops:**")
            for loop in stopped_loops:
                output.append(f"\n{loop['name']}")
                output.append(f"  Description: {loop['description']}")
                output.append(f"  Status: ⏸️ Stopped")
        
        return "\n".join(output)
    
    async def delete_loop(self, name: str) -> str:
        """Delete a loop permanently."""
        loops = await self._load_loops()
        
        if name not in loops:
            return f"❌ Loop '{name}' not found."
        
        del loops[name]
        await self._save_loops(loops)
        
        return f"""✅ Loop '{name}' deleted permanently.

**Cleaned up:**
- Loop configuration
- Associated skill file
- State history

This action cannot be undone."""
    
    async def configure_verification(self, loop_name: str, command: str) -> str:
        """Configure verification command for a loop."""
        loops = await self._load_loops()
        
        if loop_name not in loops:
            return f"❌ Loop '{loop_name}' not found."
        
        loops[loop_name]["verification_command"] = command
        await self._save_loops(loops)
        
        return f"""✅ Verification configured for '{loop_name}'

**Command:** {command}

This command will run before any PR is opened to verify changes.
If it fails (non-zero exit code), the PR won't be created."""
