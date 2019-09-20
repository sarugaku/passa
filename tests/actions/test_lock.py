# -*- coding=utf-8 -*-

import passa.actions.lock
import passa.actions.install
import passa.cli.options
import passa.models.projects
import pytest


def test_lock_one(project_directory, is_dev):
    project = passa.cli.options.Project(project_directory.strpath)
    line = "pytz"
    project.add_line_to_pipfile(line, develop=is_dev)
    retcode = passa.actions.lock.lock(project=project)
    assert retcode == 0
    lockfile_section = "default" if not is_dev else "develop"
    assert 'pytz' in project.lockfile._data[lockfile_section].keys()


def test_lock_one_with_deps(project_directory, is_dev):
    project = passa.cli.options.Project(project_directory.strpath)
    line = "requests"
    project.add_line_to_pipfile(line, develop=is_dev)
    retcode = passa.actions.lock.lock(project=project)
    assert retcode == 0
    lockfile_section = "default" if not is_dev else "develop"
    assert 'requests' in project.lockfile._data[lockfile_section].keys()
    assert 'idna' in project.lockfile._data[lockfile_section].keys()


@pytest.mark.needs_internet
def test_lock_editable(project_directory, is_dev):
    project = passa.cli.options.Project(project_directory.strpath)
    line = "-e git+https://github.com/sarugaku/shellingham.git@1.2.1#egg=shellingham"
    project.add_line_to_pipfile(line, develop=is_dev)
    retcode = passa.actions.lock.lock(project=project)
    assert retcode == 0
    lockfile_section = "default" if not is_dev else "develop"
    assert 'shellingham' in project.lockfile._data[lockfile_section].keys(), project.lockfile._data


@pytest.mark.needs_internet
def test_lock_editable_with_deps(project_directory, is_dev):
    project = passa.cli.options.Project(project_directory.strpath)
    line = "-e git+https://github.com/psf/requests.git@v2.19.1#egg=requests"
    project.add_line_to_pipfile(line, develop=is_dev)
    retcode = passa.actions.lock.lock(project=project)
    assert retcode == 0
    lockfile_section = "default" if not is_dev else "develop"
    assert 'requests' in project.lockfile._data[lockfile_section].keys()
    assert 'idna' in project.lockfile._data[lockfile_section].keys()
