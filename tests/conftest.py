# -*- coding=utf-8 -*-
import os
import pytest
import passa
import passa.models.projects
import passa.cli.options
# import mork
import passa.models.environments
import pkg_resources
import plette
import sys
import vistir

from collections import deque
from pytest_pypi.app import prepare_packages


DEFAULT_PIPFILE_CONTENTS = """
[[source]]
name = "pypi"
url = "{pypi}/simple"
verify_ssl = true

[packages]

[dev-packages]
""".strip()
TESTS_ROOT = os.path.dirname(os.path.abspath(__file__))
PYPI_VENDOR_DIR = os.path.join(TESTS_ROOT, 'pypi')

prepare_packages(PYPI_VENDOR_DIR)


@pytest.fixture(scope="session")
def working_set_extension():
    dists = set()
    passa_dist = pkg_resources.get_distribution(pkg_resources.Requirement('passa'))
    dists.add(passa_dist)
    requirements = deque(passa_dist.requires(extras=('tests', 'virtualenv')))
    while requirements:
        req = requirements.popleft()
        dist = pkg_resources.working_set.find(req)
        dists.add(dist)
        requirements.extend(dist.requires())
    return dists


@pytest.fixture(scope="function")
def virtualenv(tmpdir_factory):
    venv_dir = tmpdir_factory.mktemp("passa-testenv")
    print("Creating virtualenv {0!r}".format(venv_dir.strpath))
    venv_module = "venv" if sys.version_info[0] > 2 else "virtualenv"
    c = vistir.misc.run([sys.executable, "-m", venv_module, venv_dir.strpath],
                        return_object=True, block=True, nospin=True)
    if c.returncode == 0:
        print("Virtualenv created...")
        return venv_dir
    raise RuntimeError("Failed creating virtualenv for testing...{0!r}".format(c.err.strip()))


class _Project(passa.cli.options.Project):
    def __init__(self, root, environment=None, working_set_extension=[]):
        self.path = root
        self.working_set_extension = working_set_extension
        self.env = environment
        super(_Project, self).__init__(self.path, environment=environment)
        self.pipfile_instance = vistir.compat.Path(self.pipfile_location)
        self.lockfile_instance = vistir.compat.Path(self.lockfile_location)

    def reload(self):
        self._p = passa.models.projects.ProjectFile.read(
            os.path.join(self.path, "Pipfile"),
            plette.Pipfile,
        )
        self._l = passa.models.projects.ProjectFile.read(
            os.path.join(self.path, "Pipfile.lock"),
            plette.Lockfile,
            invalid_ok=True,
        )


@pytest.fixture(scope="function")
def project_directory(tmpdir_factory, pypi):
    project_dir = tmpdir_factory.mktemp("passa-project")
    project_dir.join("Pipfile").write(DEFAULT_PIPFILE_CONTENTS.format(pypi=pypi.url))
    with vistir.contextmanagers.cd(project_dir.strpath), vistir.contextmanagers.temp_environ():
        os.environ["PIP_INDEX_URL"] = "{}/simple".format(pypi.url)
        yield project_dir


@pytest.fixture
def tmpvenv(virtualenv, tmpdir):
    venv_srcdir = virtualenv.join("src").mkdir()
    # venv = mork.virtualenv.VirtualEnv(virtualenv.strpath)
    workingset = pkg_resources.WorkingSet(sys.path)
    venv = passa.models.environments.Environment(prefix=virtualenv.strpath, is_venv=True,
                                                 base_working_set=workingset)
    # venv.add_dist("passa")
    # venv.run(["pip", "install", "--upgrade", "mork", "setuptools"])
    with vistir.contextmanagers.temp_environ():
        os.environ["PACKAGEBUILDER_CACHE_DIR"] = tmpdir.strpath
        os.environ["PIP_QUIET"] = "1"
        os.environ["PIP_SRC"] = venv_srcdir.strpath
        venv.is_installed = lambda x: any(d for d in venv.get_distributions() if d.project_name == x)
        yield venv


@pytest.fixture(scope="function")
def project(project_directory, working_set_extension, tmpvenv):
    # resolved = tmpvenv.resolve_dist(passa_dist, tmpvenv.base_working_set)
    with tmpvenv.activated(extra_dists=list(working_set_extension)):
        project = _Project(project_directory.strpath, environment=tmpvenv, working_set_extension=working_set_extension)
        project.is_installed = lambda x: any(d for d in tmpvenv.get_working_set() if d.project_name == x)
        yield project


@pytest.fixture(params=[True, False])
def is_dev(request):
    return request.param


@pytest.fixture(params=[True, False])
def sync(request):
    return request.param
