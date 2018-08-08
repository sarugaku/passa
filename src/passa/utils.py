import contextlib
import os
import stat
import tempfile


@contextlib.contextmanager
def atomic_binary_open_for_write(target):
    """Atomically open `target` in binary mode for writing.

    This is based on Lektor's `atomic_open()` utility, but simplified a lot
    to handle only writing, and skip many multi-process/thread edge cases
    handled by Werkzeug.

    How this works:

    * Create a temp file (in the same directory of the actual target), and
      yield for surrounding code to write to it.
    * If some thing goes wrong, try to remove the temp file. The actual target
      is not touched whatsoever.
    * If everything goes well, close the temp file, and replace the actual
      target with this new file.
    """
    f = tempfile.NamedTemporaryFile(
        dir=os.path.dirname(target),
        prefix=".__atomic-write",
        mode="w+b",
        delete=False,
    )
    # set permissions to 0644
    os.chmod(f.name, stat.S_IWUSR | stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    try:
        yield f
    except BaseException:
        f.close()
        try:
            os.remove(f.name)
        except OSError:
            pass
        raise
    else:
        f.close()
        try:
            os.remove(target)  # This is needed on Windows.
        except OSError:
            pass
        os.rename(f.name, target)  # No os.replace() on Python 2.
