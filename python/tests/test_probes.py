"""Tests for evidence probes."""

import pytest

from loop_engineering_mcp.probes.runner import ProbeRunner


@pytest.fixture
def runner(tmp_path):
    return ProbeRunner(tmp_path)


@pytest.mark.asyncio
async def test_file_exists_probe(runner, tmp_path):
    f = tmp_path / "hello.txt"
    f.write_text("x")
    ok, results = await runner.run_all(
        [{"type": "file_exists", "path": "hello.txt"}], str(tmp_path)
    )
    assert ok
    assert results[0].passed


@pytest.mark.asyncio
async def test_diff_max_lines_probe(runner, tmp_path):
    ok, results = await runner.run_all(
        [{"type": "diff_max_lines", "max": 9999}], str(tmp_path)
    )
    assert ok
