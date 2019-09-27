# -*- coding=utf-8 -*-

import passa.actions.add
import passa.actions.remove
import passa.cli.options
import passa.models.projects
import pytest


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
        assert project.is_installed(pkg)
    remove = "default" if not is_dev else "dev"
    retcode = passa.actions.remove.remove(project=project, packages=[pkg,], sync=sync, only=remove)
    assert not retcode
    project.reload()
    assert pkg not in project.lockfile._data[lockfile_section].keys()
    if sync:
        assert not project.is_installed(pkg)


def test_remove_one_with_deps(project, sync, is_dev):
    add_kwargs = {
        "project": project,
        "packages": ["tablib"],
        "editables": [],
        "dev": is_dev,
        "sync": sync,
        "clean": False
    }
    retcode = passa.actions.add.add_packages(**add_kwargs)
    assert not retcode
    lockfile_section = "default" if not is_dev else "develop"
    assert 'tablib' in project.lockfile._data[lockfile_section].keys()
    assert 'xlrd' in project.lockfile._data[lockfile_section].keys()
    if sync:
        assert project.is_installed("tablib")
        assert project.is_installed("xlrd")
    remove = "default" if not is_dev else "dev"
    retcode = passa.actions.remove.remove(project=project, packages=["tablib",], sync=sync, only=remove)
    assert not retcode
    project.reload()
    assert "tablib" not in project.lockfile._data[lockfile_section].keys()
    assert "xlrd" not in project.lockfile._data[lockfile_section].keys()
    if sync:
        assert not project.is_installed("tablib")
        assert not project.is_installed("xlrd")


@pytest.mark.needs_internet
def test_remove_editable(project, sync, is_dev):
    add_kwargs = {
        "project": project,
        "packages": [],
        "editables": ["git+https://github.com/testing/demo.git#egg=demo",],
        "dev": is_dev,
        "sync": sync,
        "clean": False
    }
    retcode = passa.actions.add.add_packages(**add_kwargs)
    assert not retcode
    lockfile_section = "default" if not is_dev else "develop"
    assert 'demo' in project.lockfile._data[lockfile_section].keys()
    if sync:
        assert project.is_installed("demo")
    remove = "default" if not is_dev else "dev"
    retcode = passa.actions.remove.remove(project=project, packages=["demo",], sync=sync, only=remove)
    assert not retcode
    project.reload()
    assert "demo" not in project.lockfile._data[lockfile_section].keys()
    if sync:
        assert not project.is_installed("demo")


def test_remove_sdist(project, is_dev, sync):
    add_kwargs = {
        "project": project,
        "packages": ["docopt"],
        "editables": [],
        "dev": is_dev,
        "sync": sync,
        "clean": False
    }
    retcode = passa.actions.add.add_packages(**add_kwargs)
    assert not retcode
    lockfile_section = "default" if not is_dev else "develop"
    assert 'docopt' in project.lockfile._data[lockfile_section].keys()
    if sync:
        assert project.is_installed("docopt")
    remove = "default" if not is_dev else "dev"
    retcode = passa.actions.remove.remove(project=project, packages=["docopt",], sync=sync, only=remove)
    assert not retcode
    project.reload()
    assert "docopt" not in project.lockfile._data[lockfile_section].keys()
    if sync:
        assert not project.is_installed("docopt")
