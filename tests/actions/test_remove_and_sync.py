# -*- coding=utf-8 -*-

import passa.actions.add
import passa.actions.remove
import passa.cli.options
import passa.models.projects
import pytest
import vistir


@pytest.mark.parametrize(
    'sync', (True, False)
)
@pytest.mark.parametrize(
    'is_dev', (True, False)
)
def test_remove_one(project, sync, is_dev):
    pkg = "xlrd"
    add_kwargs = {
        "project": project,
        "packages": [pkg,],
        "editables": [],
        "dev": is_dev,
        "sync": sync,
        "clean": False
    }
    retcode = passa.actions.add.add_packages(**add_kwargs)
    assert not retcode
    lockfile_section = "default" if not is_dev else "develop"
    assert pkg in project.lockfile._data[lockfile_section].keys()
    if sync:
        assert project.venv.is_installed(pkg) or project.is_installed(pkg)
    remove = "default" if not is_dev else "dev"
    retcode = passa.actions.remove.remove(project=project, packages=[pkg,], sync=sync, only=remove)
    assert not retcode
    project.reload()
    assert pkg not in project.lockfile._data[lockfile_section].keys()
    if sync:
        assert not project.venv.is_installed(pkg)


@pytest.mark.parametrize(
    'sync', (True, False),
)
@pytest.mark.parametrize(
    'is_dev', (True, False)
)
def test_remove_one_with_deps(project, sync, is_dev):
    add_kwargs = {
        "project": project,
        "packages": ["requests",],
        "editables": [],
        "dev": is_dev,
        "sync": sync,
        "clean": False
    }
    retcode = passa.actions.add.add_packages(**add_kwargs)
    assert not retcode
    lockfile_section = "default" if not is_dev else "develop"
    assert 'requests' in project.lockfile._data[lockfile_section].keys()
    assert 'idna' in project.lockfile._data[lockfile_section].keys()
    if sync:
        c = vistir.misc.run(["{0}".format(project.venv.python), "-c", "import requests"],
                                nospin=True, block=True, return_object=True)
        assert c.returncode == 0, (c.out, c.err)
        assert project.venv.is_installed("requests") or project.is_installed("requests")
        assert project.venv.is_installed("idna") or project.is_installed("idna")
    remove = "default" if not is_dev else "dev"
    retcode = passa.actions.remove.remove(project=project, packages=["requests",], sync=sync, only=remove)
    assert not retcode
    project.reload()
    assert "requests" not in project.lockfile._data[lockfile_section].keys()
    assert "idna" not in project.lockfile._data[lockfile_section].keys()
    if sync:
        assert not project.venv.is_installed("requests")
        assert not project.venv.is_installed("idna")


@pytest.mark.parametrize(
    'sync', (True, False),
)
@pytest.mark.parametrize(
    'is_dev', (True, False)
)
def test_remove_editable(project, sync, is_dev):
    add_kwargs = {
        "project": project,
        "packages": [],
        "editables": ["git+https://github.com/sarugaku/shellingham.git@1.2.1#egg=shellingham",],
        "dev": is_dev,
        "sync": sync,
        "clean": False
    }
    retcode = passa.actions.add.add_packages(**add_kwargs)
    assert not retcode
    lockfile_section = "default" if not is_dev else "develop"
    assert 'shellingham' in project.lockfile._data[lockfile_section].keys()
    if sync:
        c = vistir.misc.run(["{0}".format(project.venv.python), "-c", "import shellingham"],
                                nospin=True, block=True, return_object=True)
        assert c.returncode == 0, (c.out, c.err)
        assert project.venv.is_installed("shellingham") or project.is_installed("shellingham")
    remove = "default" if not is_dev else "dev"
    retcode = passa.actions.remove.remove(project=project, packages=["shellingham",], sync=sync, only=remove)
    assert not retcode
    project.reload()
    assert "shellingham" not in project.lockfile._data[lockfile_section].keys()
    if sync:
        assert not project.venv.is_installed("shellingham")


@pytest.mark.parametrize(
    'sync', (True, False),
)
@pytest.mark.parametrize(
    'is_dev', (True, False)
)
def test_remove_sdist(project, is_dev, sync):
    add_kwargs = {
        "project": project,
        "packages": ["arrow"],
        "editables": [],
        "dev": is_dev,
        "sync": sync,
        "clean": False
    }
    retcode = passa.actions.add.add_packages(**add_kwargs)
    assert not retcode
    lockfile_section = "default" if not is_dev else "develop"
    assert 'arrow' in project.lockfile._data[lockfile_section].keys()
    if sync:
        c = vistir.misc.run(["{0}".format(project.venv.python), "-c", "import arrow"],
                                nospin=True, block=True, return_object=True)
        assert c.returncode == 0, (c.out, c.err)
        assert project.venv.is_installed("arrow") or project.is_installed("arrow")
    remove = "default" if not is_dev else "dev"
    retcode = passa.actions.remove.remove(project=project, packages=["arrow",], sync=sync, only=remove)
    assert not retcode
    project.reload()
    assert "arrow" not in project.lockfile._data[lockfile_section].keys()
    if sync:
        assert not project.venv.is_installed("arrow")
