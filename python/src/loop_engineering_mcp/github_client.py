"""GitHub API integration for PR creation, CI, merge, and review."""

import os
import subprocess
from dataclasses import dataclass
from typing import Any, Optional

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
    """GitHub REST API client for loop automation."""

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

    def _repo(self, repo: Optional[str] = None) -> str:
        target = repo or self.repo
        if not target:
            raise ValueError("Could not detect GitHub repo. Set GITHUB_REPO=owner/repo")
        return target

    async def _get(self, path: str, repo: Optional[str] = None) -> Any:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.API_BASE}/repos/{self._repo(repo)}{path}",
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()

    async def _post(self, path: str, json_body: dict, repo: Optional[str] = None) -> Any:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.API_BASE}/repos/{self._repo(repo)}{path}",
                headers=self._headers(),
                json=json_body,
            )
            response.raise_for_status()
            return response.json()

    async def _put(self, path: str, json_body: dict, repo: Optional[str] = None) -> Any:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.put(
                f"{self.API_BASE}/repos/{self._repo(repo)}{path}",
                headers=self._headers(),
                json=json_body,
            )
            response.raise_for_status()
            return response.json()

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
            data = await self._post(
                "/pulls",
                {
                    "title": title,
                    "body": body,
                    "head": branch,
                    "base": base_branch,
                },
            )
            return PullRequestResult(
                success=True,
                pr_number=data["number"],
                pr_url=data["html_url"],
                branch=branch,
            )

        try:
            return await retry_async(_create, max_attempts=3)
        except httpx.HTTPStatusError as e:
            try:
                detail = e.response.json()
                msg = detail.get("message", str(e))
            except Exception:
                msg = str(e)
            return PullRequestResult(success=False, error=msg)
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

    async def get_pull_request(self, pr_number: int, repo: Optional[str] = None) -> dict:
        return await self._get(f"/pulls/{pr_number}", repo=repo)

    async def get_pr_files(self, pr_number: int, repo: Optional[str] = None) -> list[dict]:
        return await self._get(f"/pulls/{pr_number}/files", repo=repo)

    async def get_pr_comments(self, pr_number: int, repo: Optional[str] = None) -> list[dict]:
        issue_comments = await self._get(f"/issues/{pr_number}/comments", repo=repo)
        review_comments = await self._get(f"/pulls/{pr_number}/comments", repo=repo)
        return list(issue_comments) + list(review_comments)

    async def get_check_runs_for_ref(
        self, ref: str, repo: Optional[str] = None
    ) -> list[dict]:
        if not self.token:
            return []
        try:
            data = await self._get(f"/commits/{ref}/check-runs", repo=repo)
            return data.get("check_runs", [])
        except Exception:
            return []

    async def merge_pull_request(
        self,
        pr_number: int,
        *,
        merge_method: str = "squash",
        repo: Optional[str] = None,
    ) -> tuple[bool, str]:
        if not self.token:
            return False, "GITHUB_TOKEN required"
        try:
            await self._put(
                f"/pulls/{pr_number}/merge",
                {"merge_method": merge_method},
                repo=repo,
            )
            return True, f"PR #{pr_number} merged"
        except Exception as e:
            return False, str(e)

    async def submit_pr_review(
        self,
        pr_number: int,
        *,
        event: str,
        body: str,
        repo: Optional[str] = None,
    ) -> tuple[bool, str]:
        if not self.token:
            return False, "GITHUB_TOKEN required"
        try:
            await self._post(
                f"/pulls/{pr_number}/reviews",
                {"event": event, "body": body},
                repo=repo,
            )
            return True, "Review submitted"
        except Exception as e:
            return False, str(e)

    async def get_pr_diff_stats(self, pr_number: int, repo: Optional[str] = None) -> dict:
        pr = await self.get_pull_request(pr_number, repo=repo)
        return {
            "additions": pr.get("additions", 0),
            "deletions": pr.get("deletions", 0),
            "changed_files": pr.get("changed_files", 0),
        }
