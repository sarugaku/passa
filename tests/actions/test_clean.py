# -*- coding=utf-8 -*-
import passa.actions.add
import passa.actions.clean


def test_clean(project):
    retcode = passa.actions.add.add_packages(["requests"], project=project)
    assert not retcode
    packages = ["requests", "chardet", "certifi", "idna"]
    c = project.env.run("pip install pytz")
    assert c.returncode == 0
    assert project.env.is_installed("pytz")
    c = project.env.run("python -c 'import pytz'")
    assert c.returncode == 0
    clean_retcode = passa.actions.clean.clean(project=project)
    assert not clean_retcode
    assert not project.env.is_installed("pytz")
    c = project.env.run("python -c 'import pytz'")
    assert c.returncode != 0
    assert all(pkg in project.lockfile.default for pkg in packages)
