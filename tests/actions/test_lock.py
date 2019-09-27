# -*- coding=utf-8 -*-

import passa.actions.lock
import passa.actions.install
import passa.cli.options
import passa.models.projects
import pytest


def test_lock_one(project, is_dev):
    line = "pytz"
    project.add_line_to_pipfile(line, develop=is_dev)
    retcode = passa.actions.lock.lock(project=project)
    assert retcode == 0
    lockfile_section = "default" if not is_dev else "develop"
    assert 'pytz' in project.lockfile._data[lockfile_section].keys()


def test_lock_one_with_deps(project, is_dev):
    line = "requests"
    project.add_line_to_pipfile(line, develop=is_dev)
    retcode = passa.actions.lock.lock(project=project)
    assert retcode == 0
    lockfile_section = "default" if not is_dev else "develop"
    assert 'requests' in project.lockfile._data[lockfile_section].keys()
    assert 'idna' in project.lockfile._data[lockfile_section].keys()


@pytest.mark.needs_internet
def test_lock_editable(project, is_dev):
    line = "-e git+https://github.com/testing/no_dep.git#egg=no_dep"
    project.add_line_to_pipfile(line, develop=is_dev)
    retcode = passa.actions.lock.lock(project=project)
    assert retcode == 0
    lockfile_section = "default" if not is_dev else "develop"
    assert 'no-dep' in project.lockfile._data[lockfile_section].keys(), project.lockfile._data


@pytest.mark.needs_internet
def test_lock_editable_with_deps(project, is_dev):
    line = "-e git+https://github.com/testing/demo.git#egg=demo"
    project.add_line_to_pipfile(line, develop=is_dev)
    retcode = passa.actions.lock.lock(project=project)
    assert retcode == 0
    lockfile_section = "default" if not is_dev else "develop"
    assert 'demo' in project.lockfile._data[lockfile_section].keys()
    assert 'requests' in project.lockfile._data[lockfile_section].keys()
