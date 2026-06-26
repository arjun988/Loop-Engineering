"""Execute verification commands with timeout and error handling."""

import asyncio
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class VerificationResult:
    """Result of running a verification command."""

    success: bool
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False
    duration_seconds: float = 0.0
    error: Optional[str] = None


class VerificationRunner:
    """Runs shell verification commands in a subprocess."""

    def __init__(self, workspace_root: Path, default_timeout: int = 600):
        self.workspace_root = workspace_root
        self.default_timeout = default_timeout

    async def run(
        self,
        command: str,
        *,
        timeout: Optional[int] = None,
        cwd: Optional[Path] = None,
    ) -> VerificationResult:
        """Run a verification command and capture output."""
        if not command or command.strip() == "echo 'No verification configured'":
            return VerificationResult(
                success=True,
                exit_code=0,
                stdout="No verification configured — skipped",
                stderr="",
            )

        work_dir = cwd or self.workspace_root
        timeout_secs = timeout or self.default_timeout
        start = asyncio.get_event_loop().time()

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(work_dir),
                env=os.environ.copy(),
            )
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout_secs
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                duration = asyncio.get_event_loop().time() - start
                return VerificationResult(
                    success=False,
                    exit_code=-1,
                    stdout="",
                    stderr=f"Verification timed out after {timeout_secs}s",
                    timed_out=True,
                    duration_seconds=duration,
                    error="timeout",
                )

            duration = asyncio.get_event_loop().time() - start
            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")
            exit_code = proc.returncode or 0

            return VerificationResult(
                success=exit_code == 0,
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                duration_seconds=duration,
            )
        except Exception as e:
            duration = asyncio.get_event_loop().time() - start
            return VerificationResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                duration_seconds=duration,
                error=str(e),
            )
