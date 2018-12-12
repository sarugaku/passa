# -*- coding=utf-8 -*-
import passa.actions.init
import passa.actions.add
import passa.cli.options
import passa.models.projects


def test_add_one(project_directory):
    project = passa.cli.options.Project(project_directory.strpath)
    retcode = passa.actions.add.add_packages(["pytz"], project=project)
    assert not retcode
    assert 'pytz' in project.lockfile.default


def test_add_one_with_deps(project_directory):
    project = passa.cli.options.Project(project_directory.strpath)
    retcode = passa.actions.add.add_packages(["requests"], project=project)
    assert not retcode
    assert 'requests' in project.lockfile.default
    assert 'idna' in project.lockfile.default
