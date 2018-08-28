import ast
import pathlib
import shutil

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
    with INIT_PY.open() as f:
        for line in f:
            if not line.startswith('__version__ = '):
                continue
            value = ast.literal_eval(line.split('=', 1)[-1].strip())
            return parver.Version.parse(value)


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


def bump_release(ctx, type_):
    if type_ not in REL_TYPES:
        raise ValueError(f'{type_} not in {REL_TYPES}')
    index = REL_TYPES.index(type_)
    prev_version = _read_version()
    next_version = prev_version.base_version().bump_release(index)
    print(f'[bump] {prev_version} -> {next_version}')
    _write_version(next_version)


@invoke.task(pre=[clean])
def build(ctx):
    ctx.run(f'python setup.py sdist bdist_wheel')


@invoke.task(pre=[build])
def upload(ctx, repo):
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


@invoke.task()
def prebump(ctx, type_):
    if type_ not in REL_TYPES:
        raise ValueError(f'{type_} not in {REL_TYPES}')
    index = REL_TYPES.index(type_)
    prev_version = _read_version()
    next_version = prev_version.bump_release(index).bump_dev()
    print(f'[bump] {prev_version} -> {next_version}')
    _write_version(next_version)
    ctx.run(f'git commit -am "Prebump to {next_version}"')


PREBUMP = 'patch'


@invoke.task()
def release(ctx, type_, repo=None, prebump_to=PREBUMP):
    """Make a new release.
    """

    bump_release(ctx, type_=type_)

    version = _read_version()
    ctx.run('towncrier')
    ctx.run(f'git commit -am "Release {version}"')
    ctx.run(f'git tag -fa {version} -m "Version {version}"')

    if repo:
        upload(ctx, repo=repo)
    else:
        print('[release] Missing --repo, skip uploading')

    prebump(ctx, type_=prebump_to)
