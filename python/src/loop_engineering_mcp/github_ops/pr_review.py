"""Automated PR review loop helpers."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiofiles


class PRReviewManager:
    """Spawn read-only PR review briefs and record verdicts."""

    def __init__(self, state_dir: Path):
        self.state_dir = state_dir
        self.reviews_file = state_dir / "pr-reviews.json"

    async def _load_reviews(self) -> dict:
        if not self.reviews_file.exists():
            return {"reviews": []}
        async with aiofiles.open(self.reviews_file, "r") as f:
            return json.loads(await f.read())

    async def _save_reviews(self, data: dict) -> None:
        async with aiofiles.open(self.reviews_file, "w") as f:
            await f.write(json.dumps(data, indent=2))

    def build_review_brief(
        self,
        *,
        pr_number: int,
        title: str,
        body: str,
        files: list[dict],
        diff_stats: dict,
    ) -> str:
        files_text = "\n".join(
            f"- `{f.get('filename')}` (+{f.get('additions', 0)}/-{f.get('deletions', 0)})"
            for f in files[:30]
        ) or "- (no files)"
        return f"""🔎 **PR review subagent: #{pr_number}**

You are an independent code reviewer. **Default: request_changes** unless evidence is strong.
Use read-only tools (Read, Grep, Glob) plus shell tests if needed.

**Title:** {title}
**Body:** {body[:1500]}

**Diff stats:** +{diff_stats.get('additions', 0)} / -{diff_stats.get('deletions', 0)} files: {diff_stats.get('changed_files', 0)}

## Files
{files_text}

## Review rubric
1. Correctness — logic errors, edge cases, regressions
2. Scope — minimal change for stated goal
3. Security — secrets, injection, auth bypass
4. Tests — adequate coverage, not disabled
5. Style — matches project conventions

## Signal-to-noise (CR-Bench principle)
Prefer **escalate** over false approval. False approvals are worse than false escalations.

## Required output JSON
```json
{{
  "verdict": "approve" | "request_changes" | "escalate",
  "confidence": 0.0-1.0,
  "comments": ["bullet findings"],
  "summary": "one paragraph"
}}
```

Then call `post_review_verdict` with pr_number, verdict, confidence, and comments.
"""

    async def post_verdict(
        self,
        *,
        pr_number: int,
        verdict: str,
        confidence: float,
        comments: list[str],
        loop_name: Optional[str] = None,
        github_client=None,
    ) -> str:
        verdict = verdict.lower()
        if verdict not in ("approve", "request_changes", "escalate"):
            verdict = "request_changes"

        if confidence < 0.85 and verdict == "approve":
            verdict = "escalate"

        data = await self._load_reviews()
        entry = {
            "pr_number": pr_number,
            "verdict": verdict,
            "confidence": confidence,
            "comments": comments,
            "loop_name": loop_name,
            "timestamp": datetime.now().isoformat(),
        }
        data.setdefault("reviews", []).append(entry)
        await self._save_reviews(data)

        gh_msg = ""
        if github_client and github_client.token:
            if verdict == "approve" and confidence >= 0.85:
                ok, msg = await github_client.submit_pr_review(
                    pr_number, event="APPROVE", body="\n".join(comments) or "LGTM"
                )
                gh_msg = f"\n**GitHub:** {'✅ Approved' if ok else '❌ ' + msg}"
            elif verdict == "request_changes":
                ok, msg = await github_client.submit_pr_review(
                    pr_number,
                    event="REQUEST_CHANGES",
                    body="\n".join(comments) or "Changes requested",
                )
                gh_msg = f"\n**GitHub:** {'📝 Changes requested' if ok else '❌ ' + msg}"

        return (
            f"✅ **Review verdict recorded: PR #{pr_number}**\n"
            f"**Verdict:** {verdict} (confidence {confidence:.0%})\n"
            f"**Comments:** {len(comments)}{gh_msg}"
        )
