# -*- coding=utf-8 -*-
import os
import pytest
import passa
import passa.cli.options
import mork.virtualenv
import sys
import vistir


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
    with vistir.contextmanagers.cd(project_dir.strpath):
        yield project_dir


@pytest.fixture(scope="function")
def virtualenv(tmpdir_factory):
    venv_dir = tmpdir_factory.mktemp("passa-testenv")
    print("Creating virtualenv {0!r}".format(venv_dir.strpath))
    c = vistir.misc.run([sys.executable, "-m", "virtualenv", venv_dir.strpath],
                            return_object=True, block=True, nospin=True)
    if c.returncode == 0:
        print("Virtualenv created...")
        return venv_dir
    raise RuntimeError("Failed creating virtualenv for testing...{0!r}".format(c.err.strip()))


class _Project(passa.cli.options.Project):
    def __init__(self, root, venv=None):
        self.path = root.strpath
        self.venv = venv
        super(_Project, self).__init__(self.path)


@pytest.fixture
def tmpvenv(virtualenv):
    return mork.virtualenv.VirtualEnv(virtualenv.strpath)


@pytest.fixture(scope="function")
def project(project_directory, tmpvenv, tmpdir):
    import pkg_resources
    passa_dist = pkg_resources.get_distribution(pkg_resources.Requirement('passa'))
    resolved = tmpvenv.resolve_dist(passa_dist, tmpvenv.base_working_set)
    with vistir.contextmanagers.temp_environ(), tmpvenv.activated(extra_dists=list(resolved)):
        os.environ["PACKAGEBUILDER_CACHE_DIR"] = tmpdir.strpath
        yield _Project(project_directory, tmpvenv)
