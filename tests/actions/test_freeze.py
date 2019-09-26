# -*- coding=utf-8 -*-
import passa.actions.add
import passa.actions.freeze
import passa.cli.options
import passa.models.projects


def test_freeze(project):
    retcode = passa.actions.add.add_packages(["requests"], project=project)
    assert not retcode
    packages = ["requests", "chardet", "certifi", "idna"]
    assert all(pkg in project.lockfile.default for pkg in packages)
    freeze_file = project.path.joinpath("requirements.txt")
    freeze_retcode = passa.actions.freeze.freeze(
        project=project, include_hashes=False, target=freeze_file.as_posix()
    )
    assert not freeze_retcode
    lines = [line.strip() for line in freeze_file.read_text().splitlines() if line.strip() != '']
    for pkg in packages:
        assert any(line.startswith(pkg) for line in lines)
