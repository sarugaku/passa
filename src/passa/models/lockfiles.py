import json

import attr
import six


DEFAULT_NEWLINES = u"\n"


class _LockFileEncoder(json.JSONEncoder):
    """A specilized JSON encoder to convert loaded data into a lock file.

    This adds a few characteristics to the encoder:

    * The JSON is always prettified with indents and spaces.
    * The output is always UTF-8-encoded text, never binary, even on Python 2.
    """
    def __init__(self, newlines=None):
        self.newlines = DEFAULT_NEWLINES if not newlines else newlines
        super(_LockFileEncoder, self).__init__(
            indent=4, separators=(",", ": "), sort_keys=True,
        )

    def encode(self, obj):
        content = super(_LockFileEncoder, self).encode(obj)
        if not isinstance(content, six.text_type):
            content = content.decode("utf-8")
        return content


def _guess_preferred_newlines(f):
    if isinstance(f.newlines, six.text_type):
        return f.newlines
    return DEFAULT_NEWLINES


@attr.s
class Lockfile(object):

    pipfile_spec = attr.ib()
    pipfile_hash = attr.ib()
    requires = attr.ib()
    sources = attr.ib()
    default = attr.ib()
    develop = attr.ib()

    def as_data(self):
        return {
            "_meta": {
                "hash": {
                    self.pipfile_hash.name: self.pipfile_hash.hexdigest(),
                },
                "pipfile-spec": self.pipfile_spec,
                "requires": self.requires.as_data(),
                "sources": [source.as_data() for source in self.sources],
            },
            "default": {
                k: v.as_pipfile()[k] for k, v in self.default.items()
            },
            "develop": {
                k: v.as_pipfile()[k] for k, v in self.develop.items()
            },
        }

    def dump(self, f, encoding=None):
        encoder = _LockFileEncoder(newlines=_guess_preferred_newlines(f))
        data = encoder.encode(self.as_data())
        if encoding:
            data = data.encode(encoding)
        f.write(data)
