# -*- coding=utf-8 -*-
import passa.actions.add
import passa.actions.clean


def test_clean(project, install_manager):
    retcode = passa.actions.add.add_packages(["requests"], project=project)
    assert not retcode
    packages = ["requests", "chardet", "certifi", "idna"]
    install_manager.install('pytz==2018.4')
    clean_retcode = passa.actions.clean.clean(project=project)
    assert not clean_retcode
    assert not project.is_installed("pytz")
    assert all(pkg in project.lockfile.default for pkg in packages)
