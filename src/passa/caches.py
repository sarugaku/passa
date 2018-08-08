import contextlib
import copy
import hashlib
import os

import appdirs
import requests

from requirementslib._compat import (
    FAVORITE_HASH, is_file_url, url_to_path,
    Link, SafeFileCache, VcsSupport,
)


CACHE_DIR = os.environ.get(
    "PIPENV_CACHE_DIR",
    appdirs.user_cache_dir("pipenv"),
)


@contextlib.contextmanager
def open_local_or_remote_file(link, session):
    """
    Open local or remote file for reading.

    :type link: pip._internal.index.Link
    :type session: requests.Session
    :raises ValueError: If link points to a local directory.
    :return: a context manager to the opened file-like object
    """
    if isinstance(link, Link):
        url = link.url_without_fragment
    else:
        url = link

    if is_file_url(link):
        # Local URL
        local_path = url_to_path(url)
        if os.path.isdir(local_path):
            raise ValueError("Cannot open directory for read: {}".format(url))
        else:
            with open(local_path, 'rb') as local_file:
                yield local_file
    else:
        # Remote URL
        headers = {"Accept-Encoding": "identity"}
        response = session.get(url, headers=headers, stream=True)
        try:
            yield response.raw
        finally:
            response.close()


class HashCache(SafeFileCache):
    """Caches hashes of PyPI artifacts so we do not need to re-download them

    Hashes are only cached when the URL appears to contain a hash in it and the cache key includes
    the hash value returned from the server). This ought to avoid ssues where the location on the
    server changes."""
    def __init__(self, *args, **kwargs):
        session = kwargs.pop('session', requests.session())
        self.session = session
        kwargs.setdefault('directory', os.path.join(CACHE_DIR, 'hash-cache'))
        super(HashCache, self).__init__(*args, **kwargs)

    def get_hash(self, location):
        # if there is no location hash (i.e., md5 / sha256 / etc) we on't want to store it
        hash_value = None
        vcs = VcsSupport()
        orig_scheme = location.scheme
        new_location = copy.deepcopy(location)
        if orig_scheme in vcs.all_schemes:
            new_location.url = new_location.url.split("+", 1)[-1]
        can_hash = new_location.hash
        if can_hash:
            # hash url WITH fragment
            hash_value = self.get(new_location.url)
        if not hash_value:
            hash_value = self._get_file_hash(new_location)
            hash_value = hash_value.encode('utf8')
        if can_hash:
            self.set(new_location.url, hash_value)
        return hash_value.decode('utf8')

    def _get_file_hash(self, location):
        h = hashlib.new(FAVORITE_HASH)
        with open_local_or_remote_file(location, self.session) as fp:
            for chunk in iter(lambda: fp.read(8096), b""):
                h.update(chunk)
        return ":".join([FAVORITE_HASH, h.hexdigest()])
