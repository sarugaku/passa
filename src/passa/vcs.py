import atexit
import os
import shutil
import tempfile

from pip_shims import VcsSupport


def _cleanup(thing):
    try:
        shutil.rmtree(thing)
    except Exception as e:
        pass    # Whatever.


def _obtrain_ref(vcs_obj, src_dir, name, rev=None):
    target_dir = os.path.join(src_dir, name)
    target_rev = vcs_obj.make_rev_options(rev)
    if not os.path.exists(target_dir):
        vcs_obj.obtain(target_dir)
    if (not vcs_obj.is_commit_id_equal(target_dir, rev) and
            not vcs_obj.is_commit_id_equal(target_dir, target_rev)):
        vcs_obj.update(target_dir, target_rev)
    return vcs_obj.get_revision(target_dir)


def _get_src():
    src = os.environ.get("PIP_SRC")
    if src:
        return src
    virtual_env = os.environ.get("VIRTUAL_ENV")
    if virtual_env:
        return os.path.join(virtual_env, "src")
    temp_src = tempfile.mkdtemp(prefix='passa-src')
    atexit.register(_cleanup, temp_src)
    return temp_src


def set_ref(requirement):
    backend = VcsSupport()._registry.get(requirement.vcs)
    vcs = backend(url=requirement.req.vcs_uri)
    src = _get_src()
    if not os.path.exists(src):
        os.makedirs(src, mode=0o775)
    name = requirement.normalized_name
    ref = _obtrain_ref(vcs, src, name, rev=requirement.req.ref)
    requirement.req.ref = ref
