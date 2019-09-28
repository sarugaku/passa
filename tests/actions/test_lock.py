# -*- coding=utf-8 -*-

import passa.actions.lock
import passa.actions.install
import passa.cli.options
import passa.models.projects
import pytest
import shutil

from tests import FIXTURES_DIR


@pytest.mark.parametrize('req,deps', [
    ('pytz', ['pytz']), ('requests', ['requests', 'idna'])
])
def test_lock_one(project, is_dev, req, deps):
    project.add_line_to_pipfile(req, develop=is_dev)
    retcode = passa.actions.lock.lock(project=project)
    assert retcode == 0
    lockfile_section = "default" if not is_dev else "develop"
    for dep in deps:
        assert dep in project.lockfile._data[lockfile_section].keys()


@pytest.mark.parametrize('line', [
    "-e git+https://github.com/testing/no_dep.git#egg=no_dep",
    "-e {}/git/github.com/testing/no_dep.git".format(FIXTURES_DIR)
])
def test_lock_editable(project, is_dev, line):
    project.add_line_to_pipfile(line, develop=is_dev)
    retcode = passa.actions.lock.lock(project=project)
    assert retcode == 0
    lockfile_section = "default" if not is_dev else "develop"
    assert 'no-dep' in project.lockfile._data[lockfile_section].keys(), project.lockfile._data


@pytest.mark.parametrize('line', [
    "-e git+https://github.com/testing/demo.git#egg=demo",
    "-e {}/git/github.com/testing/demo.git".format(FIXTURES_DIR)
])
def test_lock_editable_with_deps(project, is_dev, line):
    project.add_line_to_pipfile(line, develop=is_dev)
    retcode = passa.actions.lock.lock(project=project)
    assert retcode == 0
    lockfile_section = "default" if not is_dev else "develop"
    assert 'demo' in project.lockfile._data[lockfile_section].keys()
    assert 'requests' in project.lockfile._data[lockfile_section].keys()


@pytest.mark.parametrize('link', [
    "flask/Flask-0.12.2-py2.py3-none-any.whl",
    "flask/Flask-0.12.2.tar.gz"
])
def test_lock_file_links(project, link, pypi):
    project.add_line_to_pipfile("{}/{}".format(pypi.url, link), develop=False)
    retcode = passa.actions.lock.lock(project=project)
    assert retcode == 0
    lockfile_section = project.lockfile._data["default"]
    assert 'flask' in lockfile_section.keys()
    assert 'jinja2' in lockfile_section.keys()


def test_lock_vcs_link(project):
    project.add_line_to_pipfile("git+https://github.com/testing/demo.git#egg=demo", develop=False)
    retcode = passa.actions.lock.lock(project=project)
    assert retcode == 0
    assert 'demo' in project.lockfile._data['default'].keys()
    assert project.lockfile._data['default']['demo']['ref'] == 'c55ee5cc8230a338a8a942704a9fe7eff8f88a1c'
    assert 'requests' in project.lockfile._data['default'].keys()


def test_lock_editable_relative_path(project, is_dev):
    shutil.copytree(
        "{}/git/github.com/testing/demo.git".format(FIXTURES_DIR),
        project.path.joinpath("demo").as_posix()
    )
    project.add_line_to_pipfile("-e ./demo", develop=is_dev)
    retcode = passa.actions.lock.lock(project=project)
    assert retcode == 0
    lockfile_section = "default" if not is_dev else "develop"
    assert 'demo' in project.lockfile._data[lockfile_section].keys()
    assert 'requests' in project.lockfile._data[lockfile_section].keys()


@pytest.mark.skip(reason="TODO: fix extras locking")
def test_lock_with_extras(project):
    project.add_line_to_pipfile("requests[socks]", develop=False)
    retcode = passa.actions.lock.lock(project=project)
    assert retcode == 0
    lockfile_section = project.lockfile.default._data
    assert 'requests' in lockfile_section
    assert lockfile_section['requests']['extras'] == ['socks']
    assert 'idna' in lockfile_section
    assert 'pysocks' in lockfile_section


def test_lock_inherit_markers(project, is_dev):
    project.add_line_to_pipfile("requests; os_name == 'nt'", develop=is_dev)
    section = "develop" if is_dev else "default"
    retcode = passa.actions.lock.lock(project=project)
    assert retcode == 0
    for pkg in ('requests', 'idna'):
        assert pkg in project.lockfile._data[section]
        assert "os_name == 'nt'" in project.lockfile._data[section][pkg]['markers']
