# -*- coding=utf-8 -*-

import passa.actions.install
import passa.actions.add
import passa.cli.options
import passa.models.projects
import pytest


def test_install_one(project, is_dev):
    add_kwargs = {
        "project": project,
        "packages": ["pytz",],
        "editables": [],
        "dev": is_dev,
        "sync": False,
        "clean": False
    }
    retcode = passa.actions.add.add_packages(**add_kwargs)
    assert not retcode
    lockfile_section = "default" if not is_dev else "develop"
    assert 'pytz' in project.lockfile._data[lockfile_section].keys()
    install = passa.actions.install.install(project=project, check=True, dev=is_dev, clean=False)
    assert install == 0
    assert project.is_installed("pytz")


def test_install_one_with_deps(project, is_dev):
    add_kwargs = {
        "project": project,
        "packages": ["requests",],
        "editables": [],
        "dev": is_dev,
        "sync": False,
        "clean": False
    }
    retcode = passa.actions.add.add_packages(**add_kwargs)
    assert not retcode
    lockfile_section = "default" if not is_dev else "develop"
    assert 'requests' in project.lockfile._data[lockfile_section].keys()
    assert 'idna' in project.lockfile._data[lockfile_section].keys()
    install = passa.actions.install.install(project=project, check=True, dev=is_dev, clean=False)
    assert install == 0
    assert project.is_installed("requests")
    assert project.is_installed("idna")


@pytest.mark.needs_internet
def test_install_editable(project, is_dev):
    add_kwargs = {
        "project": project,
        "packages": [],
        "editables": ["git+https://github.com/pallets/click.git@6.7#egg=click",],
        "dev": is_dev,
        "sync": False,
        "clean": False
    }
    retcode = passa.actions.add.add_packages(**add_kwargs)
    assert not retcode
    lockfile_section = "default" if not is_dev else "develop"
    assert 'click' in project.lockfile._data[lockfile_section].keys()
    install = passa.actions.install.install(project=project, check=True, dev=is_dev, clean=False)
    assert install == 0
    project.reload()
    assert (
        project.is_installed("click")
    ), list([dist.project_name for dist in project.env.get_distributions()])


def test_install_sdist(project, is_dev):
    add_kwargs = {
        "project": project,
        "packages": ["docopt",],
        "editables": [],
        "dev": is_dev,
        "sync": False,
        "clean": False
    }
    retcode = passa.actions.add.add_packages(**add_kwargs)
    assert not retcode
    lockfile_section = "default" if not is_dev else "develop"
    assert 'docopt' in project.lockfile._data[lockfile_section].keys()
    install = passa.actions.install.install(project=project, check=True, dev=is_dev, clean=False)
    assert install == 0
    project.reload()
    assert project.is_installed("docopt")
