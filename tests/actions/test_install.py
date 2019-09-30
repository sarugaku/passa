# -*- coding=utf-8 -*-
import passa.actions.install
import passa.actions.add
import passa.cli.options
import passa.models.projects
import pytest

from tests import FIXTURES_DIR


@pytest.mark.parametrize('req,deps', [
    ('pytz', ['pytz']), ('requests', ['requests', 'idna'])
])
def test_install_one(project, is_dev, req, deps):
    add_kwargs = {
        "project": project,
        "packages": [req],
        "editables": [],
        "dev": is_dev,
        "sync": False,
        "clean": False
    }
    retcode = passa.actions.add.add_packages(**add_kwargs)
    assert not retcode
    lockfile_section = "default" if not is_dev else "develop"
    for dep in deps:
        assert dep in project.lockfile._data[lockfile_section].keys()
    install = passa.actions.install.install(project=project, check=True, dev=is_dev, clean=False)
    assert install == 0
    for dep in deps:
        assert project.is_installed(dep)


@pytest.mark.parametrize('line', [
    "git+https://github.com/testing/demo.git#egg=demo",
    "{}/git/github.com/testing/demo.git".format(FIXTURES_DIR)
])
def test_install_editable(project, is_dev, line):
    add_kwargs = {
        "project": project,
        "packages": [],
        "editables": [line],
        "dev": is_dev,
        "sync": False,
        "clean": False
    }
    retcode = passa.actions.add.add_packages(**add_kwargs)
    assert not retcode
    lockfile_section = "default" if not is_dev else "develop"
    assert 'demo' in project.lockfile._data[lockfile_section]
    assert 'requests' in project.lockfile._data[lockfile_section]
    install = passa.actions.install.install(project=project, check=True, dev=is_dev, clean=False)
    assert install == 0
    assert project.is_installed("demo")
    assert project.is_installed("requests")


@pytest.mark.parametrize('link', [
    "flask/Flask-0.12.2-py2.py3-none-any.whl",
    "flask/Flask-0.12.2.tar.gz"
])
def test_install_file_links(project, is_dev, link, pypi):
    add_kwargs = {
        "project": project,
        "packages": ["{}/{}".format(pypi.url, link)],
        "editables": [],
        "dev": is_dev,
        "sync": False,
        "clean": False
    }
    retcode = passa.actions.add.add_packages(**add_kwargs)
    assert not retcode
    lockfile_section = "default" if not is_dev else "develop"
    assert 'flask' in project.lockfile._data[lockfile_section].keys()
    install = passa.actions.install.install(project=project, check=True, dev=is_dev, clean=False)
    assert install == 0
    assert project.is_installed("flask")
    assert project.is_installed("jinja2")
