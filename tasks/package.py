import pathlib
import shutil
import zipfile

import distlib.scripts
import distlib.wheel
import invoke
import passa.internals._pip
import plette
import requirementslib


ROOT = pathlib.Path(__file__).resolve().parent.parent

PACKAGE_DIR = ROOT.joinpath('pack')

DONT_PACKAGE = {
    # Rely on the client for them.
    'pip', 'setuptools',

    'importlib',    # We only support 2.7 so this is not needed.
    'modutil',      # This breaks <3.7.
    'toml',         # Why is requirementslib still not dropping it?
    'typing',       # This breaks 2.7. We'll provide a special stub for it.
}


@invoke.task()
def clean_pack(ctx):
    if PACKAGE_DIR.exists():
        shutil.rmtree(str(PACKAGE_DIR))
        print(f'[clean_pack] Removing {PACKAGE_DIR}')


def _zip_item(path, zf, root):
    if not path.is_dir():
        if path.suffix != '.so':
            zf.write(str(path), str(path.relative_to(root)))
        return
    for c in path.iterdir():
        _zip_item(c, zf, root)


@invoke.task(pre=[clean_pack])
def pack(ctx, remove_lib=True):
    """Build a isolated runnable package.
    """
    PACKAGE_DIR.mkdir(parents=True, exist_ok=True)
    with ROOT.joinpath('Pipfile.lock').open() as f:
        lockfile = plette.Lockfile.load(f)

    libdir = PACKAGE_DIR.joinpath('lib')
    packdir = pathlib.Path(__file__).resolve().parent.joinpath('pack')

    paths = {'purelib': libdir, 'platlib': libdir}
    sources = lockfile.meta.sources._data
    maker = distlib.scripts.ScriptMaker(None, None)

    # Install packages from Pipfile.lock.
    for name, package in lockfile.default._data.items():
        if name in DONT_PACKAGE:
            continue
        package.pop('editable', None)   # Don't install things as editable.
        package.pop('markers', None)    # Always install everything.
        r = requirementslib.Requirement.from_pipfile(name, package)
        wheel = passa.internals._pip.build_wheel(
            r.as_ireq(), sources, r.hashes or None,
        )
        print(f'[pack] Installing {name}')
        wheel.install(paths, maker, lib_only=True)

    # Install fake typing module.
    shutil.copy2(str(packdir.joinpath('typing.py')), libdir)

    # Pack the lib into lib.zip.
    zipname = PACKAGE_DIR.joinpath('lib.zip')
    with zipfile.ZipFile(zipname, 'w') as zf:
        _zip_item(libdir, zf, libdir)
    print(f'Written archive {zipname}')

    # Write run.py.
    shutil.copy2(str(packdir.joinpath('run.py')), PACKAGE_DIR)
    print(f'Written entry script {PACKAGE_DIR.joinpath("run.py")}')

    if remove_lib and libdir.exists():
        print(f'Removing {libdir}')
        shutil.rmtree(str(libdir))
