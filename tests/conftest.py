# -*- coding=utf-8 -*-
import os
import six
from collections import deque, namedtuple
import shutil

import pkg_resources
import plette
import pytest
import vistir

import passa
import passa.cli.options
# import mork
import passa.models.environments
import passa.models.projects
import passa.models.synchronizers
from passa.models.caches import DependencyCache, RequiresPythonCache
from requirementslib import Requirement
from pytest_pypi.app import prepare_packages
from tests import PYPI_VENDOR_DIR, FIXTURES_DIR

DEFAULT_PIPFILE_CONTENTS = """
[[source]]
name = "pypi"
url = "{pypi}/simple"
verify_ssl = true

[packages]

[dev-packages]
""".strip()

prepare_packages(PYPI_VENDOR_DIR)

_Distro = namedtuple('Distro', 'key,version')


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


class InstallManager(passa.models.synchronizers.InstallManager):

    def __init__(self, *args, **kwargs):
        super(InstallManager, self).__init__(*args, **kwargs)
        self.working_set = set()

    def get_working_set(self):
        return self.working_set

    def is_installation_local(self, name):
        return any(name == dist.key for dist in self.working_set)

    def install(self, req):
        if isinstance(req, six.string_types):
            req = Requirement.from_line(req)
        if req.is_vcs:
            dist = _Distro(req.name, req.req.ref)
        else:
            dist = _Distro(req.name, req.get_version())
        self.working_set.add(dist)
        return True

    def remove(self, name):
        dist = next((dist for dist in self.working_set if dist.key == name), None)
        if not dist:
            return False
        self.working_set.remove(dist)
        return True


@pytest.fixture(scope="function")
def install_manager():
    return InstallManager()


class _Project(passa.cli.options.Project):
    def __init__(self, root, environment=None, working_set_extension=[]):
        self.path = vistir.compat.Path(root).absolute()
        self.working_set_extension = working_set_extension
        super(_Project, self).__init__(root, environment=environment)
        self.pipfile_instance = vistir.compat.Path(self.pipfile_location)
        self.lockfile_instance = vistir.compat.Path(self.lockfile_location)

    def reload(self):
        self._p = passa.models.projects.ProjectFile.read(
            self.path.joinpath("Pipfile").as_posix(),
            plette.Pipfile,
        )
        self._l = passa.models.projects.ProjectFile.read(
            self.path.joinpath("Pipfile.lock").as_posix(),
            plette.Lockfile,
            invalid_ok=True,
        )


@pytest.fixture(scope="function")
def project(tmpdir_factory, pypi, install_manager, mocker):
    project_dir = tmpdir_factory.mktemp("passa-project")
    project_dir.join("Pipfile").write(DEFAULT_PIPFILE_CONTENTS.format(pypi=pypi.url))
    with vistir.contextmanagers.cd(project_dir.strpath), vistir.contextmanagers.temp_environ():
        mocker.patch("passa.models.synchronizers.InstallManager", return_value=install_manager)
        cache_path = project_dir.join(".cache").strpath
        os.environ["PIP_INDEX_URL"] = "{}/simple".format(pypi.url)
        os.environ["PASSA_CACHE_DIR"] = cache_path
        mocker.patch("passa.models.caches.CACHE_DIR", cache_path)
        mocker.patch("passa.internals._pip.CACHE_DIR", cache_path)
        mocker.patch("requirementslib.models.setup_info.CACHE_DIR", cache_path)
        mocker.patch(
            "passa.internals.dependencies.DEPENDENCY_CACHE",
            DependencyCache(cache_path)
        )
        mocker.patch(
            "passa.internals.dependencies.REQUIRES_PYTHON_CACHE",
            RequiresPythonCache(cache_path)
        )
        os.environ["PIP_SRC"] = project_dir.join("src").strpath
        p = _Project(project_dir.strpath)
        p.is_installed = lambda x: install_manager.is_installation_local(x)
        yield p


def mock_git_obtain(self, location):
    url, _ = self.get_url_rev_options(self.url)
    parsed_url = six.moves.urllib_parse.urlparse(url)
    path = '{}{}'.format(parsed_url.netloc, parsed_url.path)
    source_dir = os.path.join(FIXTURES_DIR, 'git', path)
    shutil.rmtree(location, ignore_errors=True)
    shutil.copytree(source_dir, location)


@pytest.fixture(autouse=True)
def setup(mocker):
    mocker.patch("pip._internal.vcs.git.Git.obtain", new=mock_git_obtain)
    p = mocker.patch("pip._internal.vcs.git.Git.get_revision")
    p.return_value = 'c55ee5cc8230a338a8a942704a9fe7eff8f88a1c'
    yield


@pytest.fixture(params=[True, False])
def is_dev(request):
    return request.param


@pytest.fixture(params=[True, False])
def sync(request):
    return request.param
