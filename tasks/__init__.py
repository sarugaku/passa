import pathlib
import shutil
import subprocess

import invoke
import parver


ROOT = pathlib.Path(__file__).resolve().parent.parent

PACKAGE_NAME = 'passa'

INIT_PY = ROOT.joinpath('src', PACKAGE_NAME, '__init__.py')


@invoke.task()
def clean(ctx):
    """Clean previously built package artifacts.
    """
    ctx.run(f'python setup.py clean')
    dist = ROOT.joinpath('dist')
    print(f'[clean] Removing {dist}')
    if dist.exists():
        shutil.rmtree(str(dist))


def _read_version():
    out = subprocess.check_output(['git', 'tag'], encoding='ascii')
    try:
        version = max(parver.Version.parse(v).normalize() for v in (
            line.strip() for line in out.split('\n')
        ) if v)
    except ValueError:
        version = parver.Version.parse('0.0.0')
    return version


def _write_version(v):
    lines = []
    with INIT_PY.open() as f:
        for line in f:
            if line.startswith('__version__ = '):
                line = f'__version__ = {repr(str(v))}\n'
            lines.append(line)
    with INIT_PY.open('w', newline='\n') as f:
        f.write(''.join(lines))


REL_TYPES = ('major', 'minor', 'patch',)


def _bump_release(version, type_):
    if type_ not in REL_TYPES:
        raise ValueError(f'{type_} not in {REL_TYPES}')
    index = REL_TYPES.index(type_)
    next_version = version.base_version().bump_release(index)
    print(f'[bump] {version} -> {next_version}')
    return next_version


def _prebump(version, prebump):
    next_version = version.bump_release(prebump).bump_dev()
    print(f'[bump] {version} -> {next_version}')
    return next_version


PREBUMP = 'patch'


@invoke.task(pre=[clean])
def release(ctx, type_, repo, prebump=PREBUMP):
    """Make a new release.
    """
    if prebump not in REL_TYPES:
        raise ValueError(f'{type_} not in {REL_TYPES}')
    prebump = REL_TYPES.index(prebump)

    version = _read_version()
    version = _bump_release(version, type_)
    _write_version(version)

    ctx.run('towncrier')

    ctx.run(f'git commit -am "Release {version}"')

    ctx.run(f'git tag -a {version} -m "Version {version}"')

    ctx.run(f'python setup.py sdist bdist_wheel')

    dist_pattern = f'{PACKAGE_NAME.replace("-", "[-_]")}-*'
    artifacts = list(ROOT.joinpath('dist').glob(dist_pattern))
    filename_display = '\n'.join(f'  {a}' for a in artifacts)
    print(f'[release] Will upload:\n{filename_display}')
    try:
        input('[release] Release ready. ENTER to upload, CTRL-C to abort: ')
    except KeyboardInterrupt:
        print('\nAborted!')
        return

    arg_display = ' '.join(f'"{n}"' for n in artifacts)
    ctx.run(f'twine upload --repository="{repo}" {arg_display}')

    version = _prebump(version, prebump)
    _write_version(version)

    ctx.run(f'git commit -am "Prebump to {version}"')
