# -*- coding=utf-8 -*-


def test_clean_subset(project):
    from passa.actions.add import add_packages
    from passa.actions.clean import clean
    retcode = add_packages(["requests"], project=project)
    assert not retcode
    packages = ["requests", "chardet", "certifi", "idna"]
    c = project.venv.run("pip install pytz")
    assert c.returncode == 0
    c = project.venv.run("python -c 'import pytz'")
    assert c.returncode == 0
    clean_retcode = clean(project=project)
    assert not clean_retcode
    c = project.venv.run("python -c 'import pytz'")
    assert c.returncode != 0
    assert all(pkg in project.lockfile.default for pkg in packages)
