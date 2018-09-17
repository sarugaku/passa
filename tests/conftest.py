# -*- coding=utf-8 -*-
import pytest


DEFAULT_PIPFILE_CONTENTS = """
[[source]]
name = "pypi"
url = "https://pypi.org/simple"
verify_ssl = true

[packages]

[dev-packages]
""".strip()


@pytest.fixture(scope="function")
def project_directory(tmpdir_factory):
    project_dir = tmpdir_factory.mktemp("passa-project")
    project_dir.join("Pipfile").write(DEFAULT_PIPFILE_CONTENTS)
    return project_dir
