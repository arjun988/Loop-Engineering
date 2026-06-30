"""Tests for verification runner."""


import pytest

from loop_engineering_mcp.verification_runner import VerificationRunner


@pytest.fixture
def runner(tmp_path):
    return VerificationRunner(tmp_path, default_timeout=10)


@pytest.mark.asyncio
async def test_skip_no_verification(runner):
    result = await runner.run("echo 'No verification configured'")
    assert result.success is True
    assert "skipped" in result.stdout.lower()


@pytest.mark.asyncio
async def test_successful_command(runner, tmp_path):
    result = await runner.run("echo hello", cwd=tmp_path)
    assert result.success is True
    assert result.exit_code == 0
    assert "hello" in result.stdout


@pytest.mark.asyncio
async def test_failed_command(runner, tmp_path):
    result = await runner.run("exit 1", cwd=tmp_path)
    assert result.success is False
    assert result.exit_code == 1


@pytest.mark.asyncio
async def test_timeout(runner, tmp_path):
    import sys
    slow_cmd = (
        f'{sys.executable} -c "import time; time.sleep(30)"'
    )
    result = await runner.run(slow_cmd, timeout=1, cwd=tmp_path)
    assert result.success is False
    assert result.timed_out is True
