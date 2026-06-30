"""Live deploy smoke verification."""

from __future__ import annotations

from typing import Any

import httpx


class DeployVerifier:
    """HTTP marker checks against a deployed environment."""

    async def verify(self, deploy_check: dict[str, Any]) -> tuple[bool, str]:
        url = deploy_check.get("url", "")
        markers = deploy_check.get("markers") or []
        timeout = float(deploy_check.get("timeout", 30))

        if not url:
            return True, "No deploy check configured — skipped"

        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                response = await client.get(url)
                body = response.text
                if response.status_code >= 400:
                    return False, f"HTTP {response.status_code} from {url}"

                missing = [m for m in markers if m not in body]
                if missing:
                    return False, f"Missing markers in response: {missing}"
                return True, f"Deploy OK ({url}, {len(markers)} markers found)"
        except Exception as e:
            return False, str(e)

    def format_result(self, loop_name: str, passed: bool, detail: str) -> str:
        mark = "✅" if passed else "❌"
        return f"{mark} **Deploy verify: {loop_name}**\n{detail}"
