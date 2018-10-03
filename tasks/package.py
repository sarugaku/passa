import pathlib
import shutil
import zipfile

import distlib.scripts
import distlib.wheel
import invoke
import packagebuilder
import passa.models.caches
import plette
import requirementslib


ROOT = pathlib.Path(__file__).resolve().parent.parent

OUTPUT_DIR = ROOT.joinpath('pack')

STUBFILES_DIR = pathlib.Path(__file__).resolve().with_name('pack')

DONT_PACKAGE = {
    # Rely on the client for them.
    'pip', 'setuptools',

    'importlib',    # We only support 2.7 so this is not needed.
    'modutil',      # This breaks <3.7.
    'toml',         # Why is requirementslib still not dropping it?
    'typing',       # This breaks 2.7. We'll provide a special stub for it.
}

IGNORE_LIB_PATTERNS = {
    '*.pyd',    # Binary on Windows.
    '*.so',     # Binary on POSIX.
}


@invoke.task()
def clean_pack(ctx):
    if OUTPUT_DIR.exists():
        shutil.rmtree(str(OUTPUT_DIR))
        print(f'[clean-pack] Removing {OUTPUT_DIR}')


def _recursive_write_to_zip(zf, path, root=None):
    if path == pathlib.Path(zf.filename):
        return
    if root is None:
        if not path.is_dir():
            raise ValueError('root is required for non-directory path')
        root = path
    if not path.is_dir():
        zf.write(str(path), str(path.relative_to(root)))
        return
    for c in path.iterdir():
        _recursive_write_to_zip(zf, c, root)


@invoke.task(pre=[clean_pack])
def pack(ctx, remove_lib=True):
    """Build a isolated runnable package.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with ROOT.joinpath('Pipfile.lock').open() as f:
        lockfile = plette.Lockfile.load(f)

    libdir = OUTPUT_DIR.joinpath('lib')

    paths = {'purelib': libdir, 'platlib': libdir}
    sources = lockfile.meta.sources._data
    maker = distlib.scripts.ScriptMaker(None, None)

    # Install packages from Pipfile.lock.
    for name, package in lockfile.default._data.items():
        if name in DONT_PACKAGE:
            continue
        print(f'[pack] Installing {name}')
        package.pop('editable', None)   # Don't install things as editable.
        package.pop('markers', None)    # Always install everything.
        r = requirementslib.Requirement.from_pipfile(name, package)
        wheel = packagebuilder._pip.build_wheel(
            r.as_ireq(), sources, r.hashes or None, cache_dir=passa.models.caches.CACHE_DIR
        )
        wheel.install(paths, maker, lib_only=True)

    for pattern in IGNORE_LIB_PATTERNS:
        for path in libdir.rglob(pattern):
            print(f'[pack] Removing {path}')
            path.unlink()

    # Pack everything into ZIP.
    zipname = OUTPUT_DIR.joinpath('passa.zip')
    with zipfile.ZipFile(zipname, 'w') as zf:
        _recursive_write_to_zip(zf, OUTPUT_DIR)
        _recursive_write_to_zip(zf, STUBFILES_DIR)
    print(f'[pack] Written archive {zipname}')

    if remove_lib and libdir.exists():
        print(f'[pack] Removing {libdir}')
        shutil.rmtree(str(libdir))
