from __future__ import annotations

import dataclasses
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

import pytest
import yaml

import docker
import docker.errors
from sweagent import CONFIG_DIR
from sweagent.environment.swe_env import EnvHook, EnvironmentArguments, SWEEnv


@pytest.fixture(scope="module")
def test_env_args(
    tmpdir_factory,
):
    """This will use a persistent container"""
    local_repo_path = tmpdir_factory.getbasetemp() / "swe-agent-test-repo"
    clone_cmd = ["git", "clone", "https://github.com/klieret/swe-agent-test-repo", local_repo_path]
    subprocess.run(clone_cmd, check=True)
    data_path = local_repo_path / "problem_statements" / "1.md"
    test_env_args = EnvironmentArguments(
        data_path=str(data_path),
        repo_path=str(local_repo_path),
        image_name="sweagent/swe-agent:latest",
        container_name="test-container-this-is-a-random-string",
        verbose=True,
    )
    yield test_env_args
    # Cleanup (after session ends)
    client = docker.from_env()
    # fixme (?): What happens if user changed container_name?
    try:
        container = client.containers.get(test_env_args.container_name)
        container.remove(force=True)
    except docker.errors.NotFound:
        # Can happen if this fixture never runs because we only do a partial
        # test run
        pass


@contextmanager
def swe_env_context(env_args):
    """Context manager to make sure we close the shell on the container
    so that we can reuse it.
    """

    env = SWEEnv(env_args)
    try:
        yield env
    finally:
        env.close()


@pytest.mark.slow()
def test_init_swe_env(test_env_args):
    with swe_env_context(test_env_args) as env:
        env.reset()


@pytest.mark.slow()
def test_init_swe_env_conservative_clone(test_env_args):
    with mock.patch.dict("os.environ", {"SWE_AGENT_CLONE_METHOD": "full"}):
        with swe_env_context(test_env_args) as env:
            env.reset()


@pytest.mark.slow()
def test_init_swe_env_non_persistent(test_env_args):
    test_env_args = dataclasses.replace(test_env_args, container_name=None)
    with swe_env_context(test_env_args) as env:
        env.reset()


@pytest.mark.slow()
def test_init_swe_env_cached_task_image(test_env_args):
    test_env_args = dataclasses.replace(test_env_args, cache_task_images=True, container_name=None)
    start = time.perf_counter()
    with swe_env_context(test_env_args) as env:
        env.reset()
    duration_no_cache = time.perf_counter() - start
    start = time.perf_counter()
    # now it should be cached, so let's run again
    image_prefix = None
    with swe_env_context(test_env_args) as env:
        env.reset()
        image_prefix = env.cached_image_prefix
    assert image_prefix
    duration_cache = time.perf_counter() - start
    assert duration_cache < duration_no_cache
    # Retrieve all images with a prefix "prefix"
    client = docker.from_env()
    # Remove the images
    for image in client.images.list():
        if not image.tags:
            continue
        if not image.tags[0].startswith(image_prefix):
            continue
        client.images.remove(image.id)


@pytest.mark.slow()
def test_execute_setup_script(tmp_path, test_env_args):
    test_script = "echo 'hello world'"
    script_path = Path(tmp_path / "test_script.sh")
    script_path.write_text(test_script)
    test_env_args = dataclasses.replace(test_env_args, environment_setup=script_path)
    with swe_env_context(test_env_args) as env:
        env.reset()


@pytest.mark.slow()
def test_execute_environment(tmp_path, test_env_args, capsys):
    test_env = {
        "python": "3.6",
        "packages": "pytest",
        "pip_packages": ["tox"],
        "install": "python -m pip install --upgrade pip && python -m pip install -e .",
    }
    env_config_path = Path(tmp_path / "env_config.yml")
    env_config_path.write_text(yaml.dump(test_env))
    # Make sure we don't use persistent container, else we might have already installed the conda environment
    test_env_args = dataclasses.replace(test_env_args, environment_setup=env_config_path, container_name=None)
    with swe_env_context(test_env_args) as env:
        env.reset()
    out = capsys.readouterr().out
    print(out)
    assert "Cloned python conda environment" not in out


@pytest.mark.slow()
def test_execute_environment_default(test_env_args):
    env_config_paths = (CONFIG_DIR / "environment_setup").iterdir()
    assert env_config_paths
    # Make sure we don't use persistent container, else we might have already installed the conda environment
    test_env_args = dataclasses.replace(test_env_args, container_name=None)
    for env_config_path in env_config_paths:
        if env_config_path.suffix not in [".yaml", ".yml", ".sh"]:
            continue
        print(env_config_path)
        test_env_args = dataclasses.replace(test_env_args, environment_setup=env_config_path)
        with swe_env_context(test_env_args) as env:
            env.reset()


@pytest.mark.slow()
def test_execute_environment_clone_python(tmp_path, test_env_args, capsys):
    """This should clone the existing python 3.10 conda environment for speedup"""
    test_env = {
        "python": "3.10",
        "packages": "pytest",
        "pip_packages": ["tox"],
        "install": "python -m pip install --upgrade pip && python -m pip install -e .",
    }
    env_config_path = Path(tmp_path / "env_config.yml")
    env_config_path.write_text(yaml.dump(test_env))
    # Make sure we don't use persistent container, else we might have already installed the conda environment
    test_env_args = dataclasses.replace(test_env_args, environment_setup=env_config_path, container_name=None)
    with swe_env_context(test_env_args) as env:
        env.reset()
    out = capsys.readouterr().out
    print(out)
    assert "Cloned python conda environment" in out


@pytest.mark.slow()
def test_open_pr(test_env_args):
    test_env_args = dataclasses.replace(
        test_env_args,
        data_path="https://github.com/klieret/swe-agent-test-repo/issues/1",
        repo_path="",
    )
    with swe_env_context(test_env_args) as env:
        env.reset()
        env.open_pr(_dry_run=True, trajectory=[])


@pytest.mark.slow()
def test_interrupt_close(test_env_args):
    with swe_env_context(test_env_args) as env:
        env.reset()
        env.interrupt()


@pytest.mark.slow()
def test_communicate_old(test_env_args):
    with mock.patch.dict("os.environ", {"SWE_AGENT_COMMUNICATE_METHOD": "processes"}):
        with swe_env_context(test_env_args) as env:
            env.reset()


@pytest.mark.slow()
def test_env_with_hook(test_env_args):
    with swe_env_context(test_env_args) as env:
        env.add_hook(EnvHook())
        env.reset()


def test_invalid_config():
    with pytest.raises(ValueError, match=".*Not allowed.*"):
        EnvironmentArguments(
            data_path=".",
            container_name="test",
            cache_task_images=True,
        )
