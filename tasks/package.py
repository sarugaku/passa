import pathlib
import shutil
import zipfile

import distlib.scripts
import distlib.wheel
import invoke
import passa._pip
import plette
import requirementslib


ROOT = pathlib.Path(__file__).resolve().parent.parent

PACKAGE_DIR = ROOT.joinpath('pack')

PACKAGE_LIB = PACKAGE_DIR.joinpath('lib')

PACKAGE_ZIP  = PACKAGE_DIR.joinpath('lib.zip')

DONT_PACKAGE = {
    'pip', 'setuptools',
    'modutil',  # This breaks Python < 3.7.
    'toml',     # Why is requirementslib still not dropping it?
}


@invoke.task()
def clean_pack(ctx):
    for path in (PACKAGE_LIB, PACKAGE_ZIP):
        if not path.exists():
            continue
        print(f'[clean_pack] Removing {path}')
        if path.is_dir():
            shutil.rmtree(str(path))
        else:
            path.unlink()


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

    paths = {'purelib': PACKAGE_LIB, 'platlib': PACKAGE_LIB}
    sources = lockfile.meta.sources._data
    maker = distlib.scripts.ScriptMaker(None, None)

    for name, package in lockfile.default._data.items():
        if name in DONT_PACKAGE:
            continue
        package.pop('editable', None)   # Don't install things as editable.
        package.pop('markers', None)    # Always install everything.
        r = requirementslib.Requirement.from_pipfile(name, package)
        wheel = passa._pip.build_wheel(r.as_ireq(), sources, r.hashes or None)
        print(f'[pack] Installing {name}')
        wheel.install(paths, maker, lib_only=True)

    with zipfile.ZipFile(PACKAGE_ZIP, 'w') as zf:
        _zip_item(PACKAGE_LIB, zf, PACKAGE_LIB)

    print(f'Written archive {PACKAGE_ZIP}')

    if remove_lib and PACKAGE_LIB.exists():
        print(f'Removing {PACKAGE_LIB}')
        shutil.rmtree(str(PACKAGE_LIB))
