"""End-to-end tests for the jubilant CLI (jubilant/_main.py)."""

from __future__ import annotations

import pathlib
import re
import subprocess
import sys
import uuid

import pytest

import jubilant

# The entry point script installed by setuptools always lives in the same bin/
# directory as the Python executable.  Using this path means we do not rely on
# the venv being activated, PATH, or ``python -m jubilant`` (which requires a
# __main__.py that this package intentionally does not have).
_JUBILANT_BIN = str(pathlib.Path(sys.executable).parent / 'jubilant')


def run_cli(*args: str, model: str | None = None) -> subprocess.CompletedProcess[str]:
    """Run the jubilant CLI entry-point script as a subprocess.

    Resolves the script via the same interpreter directory as pytest, so the
    correct venv is always used without requiring it to be activated.
    """
    cmd = [_JUBILANT_BIN, *args]
    if model is not None:
        cmd += ['--model', model]
    return subprocess.run(cmd, capture_output=True, text=True)


@pytest.fixture(scope='module')
def deploy_snappass(juju: jubilant.Juju) -> None:
    juju.deploy('snappass-test')
    juju.wait(jubilant.all_active)


@pytest.mark.machine
def deploy_ubuntu(juju: jubilant.Juju) -> None:
    juju.deploy('ubuntu')
    juju.wait(jubilant.all_active)


pytestmark = pytest.mark.dual


def test_wait_already_active(juju: jubilant.Juju) -> None:
    result = run_cli('wait', 'jubilant.all_active(status)', model=juju.model)
    assert result.returncode == 0


def test_wait_successes(juju: jubilant.Juju) -> None:
    result = run_cli('wait', 'jubilant.all_active(status)', '--successes', '1', model=juju.model)
    assert result.returncode == 0


def test_verbose_emits_debug_output(juju: jubilant.Juju) -> None:
    result = run_cli('wait', 'jubilant.all_active(status)', '--verbose', model=juju.model)
    assert result.returncode == 0
    assert 'DEBUG' in result.stderr


def test_default_emits_info_output(juju: jubilant.Juju) -> None:
    result = run_cli('wait', 'jubilant.all_active(status)', model=juju.model)
    assert result.returncode == 0
    assert 'Ready condition succeeded' in result.stderr


def test_quiet_suppresses_info_output(juju: jubilant.Juju) -> None:
    result = run_cli('wait', 'jubilant.all_active(status)', '--quiet', model=juju.model)
    assert result.returncode == 0
    assert 'Ready condition succeeded' not in result.stderr


def test_wait_error_condition(juju: jubilant.Juju) -> None:
    result = run_cli('wait', 'False', '--error', 'True', '--timeout', '10', model=juju.model)
    assert result.returncode == 1


def test_wait_timeout(juju: jubilant.Juju) -> None:
    result = run_cli('wait', 'False', '--timeout', '3', '--delay', '1', model=juju.model)
    assert result.returncode == 124


def test_wait_unknown_model() -> None:
    unknown = f'no-such-model-{uuid.uuid4().hex[:8]}'
    result = run_cli('wait', 'True', model=unknown)
    assert result.returncode != 0


def test_version() -> None:
    result = run_cli('version')
    assert result.returncode == 0
    assert re.match(r'^\d+\.\d+\.\d+$', result.stdout.strip())


def test_invalid_argument(juju: jubilant.Juju) -> None:
    result = run_cli('wait', '--unknown-flag', model=juju.model)
    assert result.returncode != 0


def test_wait_exception_in_expression(juju: jubilant.Juju) -> None:
    result = run_cli('wait', '0/0', model=juju.model)
    assert result.returncode != 0
    assert 'ZeroDivisionError' in result.stderr


def test_wait_undefined_name_in_expression(juju: jubilant.Juju) -> None:
    result = run_cli('wait', 'os.name', model=juju.model)
    assert result.returncode != 0
    assert 'NameError' in result.stderr


def test_quiet_still_prints_errors(juju: jubilant.Juju) -> None:
    result = run_cli(
        'wait', 'False', '--timeout', '3', '--delay', '1', '--quiet', model=juju.model
    )
    assert result.returncode == 124
    assert 'timed out' in result.stderr
