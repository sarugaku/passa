# -*- coding=utf-8 -*-
import passa.actions.init
import passa.actions.add
import passa.cli.options
import passa.models.projects


def test_add_one(project, is_dev, sync):
    retcode = passa.actions.add.add_packages(["pytz"], project=project, dev=is_dev, sync=sync)
    assert not retcode
    section = project.lockfile.develop if is_dev else project.lockfile.default
    assert section['pytz']['version'] == '==2018.4'
    assert len(section['pytz']['hashes']) > 0
    if sync:
        assert project.is_installed('pytz')


def test_add_one_with_deps(project, is_dev, sync):
    retcode = passa.actions.add.add_packages(["requests"], project=project, dev=is_dev, sync=sync)
    assert not retcode
    section = project.lockfile.develop if is_dev else project.lockfile.default
    assert 'requests' in section
    assert 'idna' in section
    if sync:
        assert project.is_installed('requests')
        assert project.is_installed('idna')
