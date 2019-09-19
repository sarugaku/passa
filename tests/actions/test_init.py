# -*- coding=utf-8 -*-

import pytest
import os

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


def test_init_inherit_pip_source(tmpdir):
    pip_config_dir = os.path.join(
        os.path.expanduser('~'),
        "pip" if os.name == "nt" else ".pip"
    )
    if not os.path.exists(pip_config_dir):
        os.makedirs(pip_config_dir)
    pip_config_path = os.path.join(pip_config_dir, "pip.ini" if os.name == "nt" else "pip.conf")
    with open(pip_config_path, 'w') as f:
        f.write('[global]\nindex-url=https://foo.pypi.org/simple')
    try:
        init_retcode = passa.actions.init.init_project(root=tmpdir.strpath)
        assert init_retcode == 0
        project = passa.cli.options.Project(tmpdir.strpath)
        assert project.pipfile.source._data[0]['url'] == 'https://foo.pypi.org/simple'
    finally:
        os.remove(pip_config_path)
