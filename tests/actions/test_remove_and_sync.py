# -*- coding=utf-8 -*-

import passa.actions.add
import passa.actions.remove
import passa.cli.options
import passa.models.projects
import pytest
import vistir


def test_remove_one(project, sync, is_dev):
    pkg = "xlrd"
    add_kwargs = {
        "project": project,
        "packages": [pkg,],
        "editables": [],
        "dev": is_dev,
        "sync": sync,
        "clean": False
    }
    retcode = passa.actions.add.add_packages(**add_kwargs)
    assert not retcode
    lockfile_section = "default" if not is_dev else "develop"
    assert pkg in project.lockfile._data[lockfile_section].keys()
    if sync:
        assert project.env.is_installed(pkg) or project.is_installed(pkg)
    remove = "default" if not is_dev else "dev"
    retcode = passa.actions.remove.remove(project=project, packages=[pkg,], sync=sync, only=remove)
    assert not retcode
    project.reload()
    assert pkg not in project.lockfile._data[lockfile_section].keys()
    if sync:
        assert not project.env.is_installed(pkg)


def test_remove_one_with_deps(project, sync, is_dev):
    add_kwargs = {
        "project": project,
        "packages": ["tablib"],
        "editables": [],
        "dev": is_dev,
        "sync": sync,
        "clean": False
    }
    retcode = passa.actions.add.add_packages(**add_kwargs)
    assert not retcode
    lockfile_section = "default" if not is_dev else "develop"
    assert 'tablib' in project.lockfile._data[lockfile_section].keys()
    assert 'xlrd' in project.lockfile._data[lockfile_section].keys()
    if sync:
        c = vistir.misc.run(["{0}".format(project.env.python), "-c", "import tablib"],
                            nospin=True, block=True, return_object=True)
        assert c.returncode == 0, (c.out, c.err)
        assert project.env.is_installed("tablib") or project.is_installed("tablib")
        assert project.env.is_installed("xlrd") or project.is_installed("xlrd")
    remove = "default" if not is_dev else "dev"
    retcode = passa.actions.remove.remove(project=project, packages=["tablib",], sync=sync, only=remove)
    assert not retcode
    project.reload()
    assert "tablib" not in project.lockfile._data[lockfile_section].keys()
    assert "xlrd" not in project.lockfile._data[lockfile_section].keys()
    if sync:
        assert not project.env.is_installed("django")
        assert not project.env.is_installed("xlrd")


@pytest.mark.needs_internet
def test_remove_editable(project, sync, is_dev):
    add_kwargs = {
        "project": project,
        "packages": [],
        "editables": ["git+https://github.com/pallets/click.git@6.7#egg=click",],
        "dev": is_dev,
        "sync": sync,
        "clean": False
    }
    retcode = passa.actions.add.add_packages(**add_kwargs)
    assert not retcode
    lockfile_section = "default" if not is_dev else "develop"
    assert 'click' in project.lockfile._data[lockfile_section].keys()
    if sync:
        c = vistir.misc.run(["{0}".format(project.env.python), "-c", "import click"],
                            nospin=True, block=True, return_object=True)
        assert c.returncode == 0, (c.out, c.err)
        assert project.env.is_installed("click") or project.is_installed("click")
    remove = "default" if not is_dev else "dev"
    retcode = passa.actions.remove.remove(project=project, packages=["click",], sync=sync, only=remove)
    assert not retcode
    project.reload()
    assert "click" not in project.lockfile._data[lockfile_section].keys()
    if sync:
        assert not project.env.is_installed("click")


def test_remove_sdist(project, is_dev, sync):
    add_kwargs = {
        "project": project,
        "packages": ["docopt"],
        "editables": [],
        "dev": is_dev,
        "sync": sync,
        "clean": False
    }
    retcode = passa.actions.add.add_packages(**add_kwargs)
    assert not retcode
    lockfile_section = "default" if not is_dev else "develop"
    assert 'docopt' in project.lockfile._data[lockfile_section].keys()
    if sync:
        c = vistir.misc.run(["{0}".format(project.env.python), "-c", "import docopt"],
                            nospin=True, block=True, return_object=True)
        assert c.returncode == 0, (c.out, c.err)
        assert project.env.is_installed("docopt") or project.is_installed("docopt")
    remove = "default" if not is_dev else "dev"
    retcode = passa.actions.remove.remove(project=project, packages=["docopt",], sync=sync, only=remove)
    assert not retcode
    project.reload()
    assert "docopt" not in project.lockfile._data[lockfile_section].keys()
    if sync:
        assert not project.env.is_installed("docopt")
