# -*- coding=utf-8 -*-

import pytest

import passa.actions.init
import passa.cli.options


def test_init(tmpdir):
    init_retcode = passa.actions.init.init_project(root=tmpdir.strpath)
    assert init_retcode == 0
    project = passa.cli.options.Project(tmpdir.strpath)
    assert project.pipfile.packages._data == {}
    assert project.pipfile.dev_packages._data == {}


def test_init_exists(project_directory):
    with pytest.raises(RuntimeError, match=r'.* is already a Pipfile project'):
        passa.actions.init.init_project(root=project_directory.strpath)
