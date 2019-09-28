# -*- coding=utf-8 -*-
import os
import passa.actions.init
import passa.actions.add
import passa.cli.options
import passa.models.projects
import pytest


@pytest.mark.parametrize('req,deps', [
    ('pytz', ['pytz']), ('requests', ['requests', 'idna'])
])
def test_add_one(project, is_dev, sync, req, deps):
    retcode = passa.actions.add.add_packages([req], project=project, dev=is_dev, sync=sync)
    assert not retcode
    section = project.lockfile.develop if is_dev else project.lockfile.default
    for dep in deps:
        assert dep in section._data
        if sync:
            assert project.is_installed(dep)


def test_add_one_with_markers(project, is_dev):
    retcode = passa.actions.add.add_packages(
        ["requests; os_name == 'nt'"],
        project=project, dev=is_dev, sync=True
    )
    assert not retcode
    for dep in ('requests', 'idna'):
        if os.name == 'nt':
            assert project.is_installed(dep)
        else:
            assert not project.is_installed(dep)
