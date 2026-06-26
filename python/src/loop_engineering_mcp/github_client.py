"""GitHub API integration for PR creation."""

import os
import subprocess
from dataclasses import dataclass
from typing import Optional

import httpx

from .retry import retry_async


@dataclass
class PullRequestResult:
    """Result of creating a pull request."""

    success: bool
    pr_number: Optional[int] = None
    pr_url: Optional[str] = None
    branch: Optional[str] = None
    error: Optional[str] = None


class GitHubClient:
    """Creates branches and pull requests via the GitHub REST API."""

    API_BASE = "https://api.github.com"

    def __init__(
        self,
        token: Optional[str] = None,
        repo: Optional[str] = None,
        default_branch: str = "main",
    ):
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.repo = repo or os.environ.get("GITHUB_REPO") or self._detect_repo()
        self.default_branch = default_branch or os.environ.get("GITHUB_DEFAULT_BRANCH", "main")

    def _detect_repo(self) -> Optional[str]:
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                return None
            url = result.stdout.strip()
            # Handle git@github.com:owner/repo.git and https://github.com/owner/repo.git
            if "github.com" in url:
                parts = url.rstrip(".git").split("/")
                if len(parts) >= 2:
                    return f"{parts[-2]}/{parts[-1]}"
            return None
        except Exception:
            return None

    def _headers(self) -> dict[str, str]:
        if not self.token:
            raise ValueError("GITHUB_TOKEN environment variable is required")
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def create_pull_request(
        self,
        *,
        title: str,
        body: str,
        branch: str,
        base: Optional[str] = None,
    ) -> PullRequestResult:
        """Create a pull request on GitHub."""
        if not self.repo:
            return PullRequestResult(
                success=False,
                error="Could not detect GitHub repo. Set GITHUB_REPO=owner/repo",
            )

        base_branch = base or self.default_branch

        async def _create() -> PullRequestResult:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.API_BASE}/repos/{self.repo}/pulls",
                    headers=self._headers(),
                    json={
                        "title": title,
                        "body": body,
                        "head": branch,
                        "base": base_branch,
                    },
                )
                if response.status_code == 422:
                    data = response.json()
                    errors = data.get("errors", [])
                    msg = errors[0].get("message") if errors else data.get("message", "Validation failed")
                    return PullRequestResult(success=False, error=msg)
                response.raise_for_status()
                data = response.json()
                return PullRequestResult(
                    success=True,
                    pr_number=data["number"],
                    pr_url=data["html_url"],
                    branch=branch,
                )

        try:
            return await retry_async(_create, max_attempts=3)
        except Exception as e:
            return PullRequestResult(success=False, error=str(e))

    async def push_branch(self, branch: str, cwd: Optional[str] = None) -> tuple[bool, str]:
        """Push the current branch to origin."""
        try:
            result = subprocess.run(
                ["git", "push", "-u", "origin", branch],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=cwd,
            )
            if result.returncode != 0:
                return False, result.stderr or result.stdout
            return True, "Branch pushed successfully"
        except Exception as e:
            return False, str(e)
