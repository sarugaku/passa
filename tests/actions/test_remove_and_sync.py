# -*- coding=utf-8 -*-

import passa.actions.add
import passa.actions.remove
import passa.cli.options
import passa.models.projects
import pytest

from tests import FIXTURES_DIR


@pytest.mark.parametrize('req,deps', [
    ('pytz', ['pytz']), ('requests', ['requests', 'idna'])
])
def test_remove_one(project, sync, is_dev, req, deps):
    add_kwargs = {
        "project": project,
        "packages": [req],
        "editables": [],
        "dev": is_dev,
        "sync": sync,
        "clean": False
    }
    retcode = passa.actions.add.add_packages(**add_kwargs)
    assert not retcode
    lockfile_section = "default" if not is_dev else "develop"
    for pkg in deps:
        assert pkg in project.lockfile._data[lockfile_section].keys()
        if sync:
            assert project.is_installed(pkg)
    remove = "default" if not is_dev else "dev"
    retcode = passa.actions.remove.remove(project=project, packages=[req], sync=sync, only=remove)
    assert not retcode
    project.reload()
    for pkg in deps:
        assert pkg not in project.lockfile._data[lockfile_section].keys()
        if sync:
            assert not project.is_installed(pkg)


@pytest.mark.parametrize('line', [
    "git+https://github.com/testing/demo.git#egg=demo",
    "{}/git/github.com/testing/demo.git".format(FIXTURES_DIR)
])
def test_remove_editable(project, sync, is_dev, line):
    add_kwargs = {
        "project": project,
        "packages": [],
        "editables": [line],
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


@pytest.mark.parametrize('link', [
    "flask/Flask-0.12.2-py2.py3-none-any.whl",
    "flask/Flask-0.12.2.tar.gz"
])
def test_remove_file_links(project, is_dev, sync, pypi, link):
    add_kwargs = {
        "project": project,
        "packages": ["{}/{}".format(pypi.url, link)],
        "editables": [],
        "dev": is_dev,
        "sync": sync,
        "clean": False
    }
    retcode = passa.actions.add.add_packages(**add_kwargs)
    assert not retcode
    lockfile_section = "default" if not is_dev else "develop"
    assert 'flask' in project.lockfile._data[lockfile_section].keys()
    if sync:
        assert project.is_installed("flask")
        assert project.is_installed("jinja2")
    remove = "default" if not is_dev else "dev"
    retcode = passa.actions.remove.remove(project=project, packages=["flask"], sync=sync, only=remove)
    assert not retcode
    project.reload()
    assert "flask" not in project.lockfile._data[lockfile_section].keys()
    if sync:
        assert not project.is_installed("flask")
        assert not project.is_installed("jinja2")
