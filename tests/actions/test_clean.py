# -*- coding=utf-8 -*-
from passa.actions.add import add_packages
from passa.cli.options import Project
import vistir


def test_clean_subset(project_directory):
    with vistir.contextmanagers.cd(project_directory.strpath):
        project = Project(project_directory.strpath)
        retcode = add_packages(["requests"], project=project)
        assert not retcode
        packages = ["requests", "chardet", "certifi", "idna"]
        assert all(pkg in project.lockfile.default for pkg in packages)
        import passa.actions.clean
        pass
        # clean_retcode = passa.actions.clean.clean(project=project)
        # assert not clean_retcode
        # assert project.lockfile.default._data == {}
