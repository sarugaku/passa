# -*- coding=utf-8 -*-

import passa.actions.lock
import passa.actions.install
import passa.cli.options
import passa.models.projects
import pytest


@pytest.mark.parametrize(
    'is_dev', (True, False)
)
def test_lock_one(project, is_dev):
    line = "pytz"
    project.add_line_to_pipfile(line, develop=is_dev)
    retcode = passa.actions.lock.lock(project=project)
    project.reload()
    assert retcode == 0
    lockfile_section = "default" if not is_dev else "develop"
    assert 'pytz' in project.lockfile._data[lockfile_section].keys()
    install = passa.actions.install.install(project=project, check=True, dev=is_dev, clean=False)
    assert install == 0


@pytest.mark.parametrize(
    'is_dev', (True, False)
)
def test_lock_one_with_deps(project, is_dev):
    line = "requests"
    project.add_line_to_pipfile(line, develop=is_dev)
    retcode = passa.actions.lock.lock(project=project)
    project.reload()
    assert retcode == 0
    lockfile_section = "default" if not is_dev else "develop"
    assert 'requests' in project.lockfile._data[lockfile_section].keys()
    assert 'idna' in project.lockfile._data[lockfile_section].keys()
    install = passa.actions.install.install(project=project, check=True, dev=is_dev, clean=False)
    assert install == 0


@pytest.mark.parametrize(
    'is_dev', (True, False)
)
def test_lock_editable(project, is_dev):
    line = "-e git+https://github.com/sarugaku/shellingham.git@1.2.1#egg=shellingham"
    project.add_line_to_pipfile(line, develop=is_dev)
    retcode = passa.actions.lock.lock(project=project)
    project.reload()
    assert retcode == 0
    lockfile_section = "default" if not is_dev else "develop"
    assert 'shellingham' in project.lockfile._data[lockfile_section].keys(), project.lockfile._data
    install = passa.actions.install.install(project=project, check=True, dev=is_dev, clean=False)
    assert install == 0
