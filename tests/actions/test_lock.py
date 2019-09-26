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
    line = "-e git+https://github.com/pallets/click.git@6.7#egg=click"
    project.add_line_to_pipfile(line, develop=is_dev)
    retcode = passa.actions.lock.lock(project=project)
    assert retcode == 0
    lockfile_section = "default" if not is_dev else "develop"
    assert 'click' in project.lockfile._data[lockfile_section].keys(), project.lockfile._data


@pytest.mark.needs_internet
def test_lock_editable_with_deps(project, is_dev):
    line = "-e git+https://github.com/sarugaku/plette.git@0.2.2#egg=plette"
    project.add_line_to_pipfile(line, develop=is_dev)
    retcode = passa.actions.lock.lock(project=project)
    assert retcode == 0
    lockfile_section = "default" if not is_dev else "develop"
    assert 'plette' in project.lockfile._data[lockfile_section].keys()
    assert 'tomlkit' in project.lockfile._data[lockfile_section].keys()
