"""Tests for deploy verification."""

import pytest

from loop_engineering_mcp.deploy_verify import DeployVerifier


@pytest.mark.asyncio
async def test_skip_when_no_url():
    verifier = DeployVerifier()
    passed, msg = await verifier.verify({})
    assert passed is True
