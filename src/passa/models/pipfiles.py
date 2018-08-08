from __future__ import absolute_import, print_function, unicode_literals

import hashlib
import json

import attr
import six
import tomlkit

from requirementslib import Requirement

from . import sections


DEFAULT_SOURCES = [
    {
        'url': 'https://pypi.org/simple',
        'verify_ssl': True,
        'name': 'pypi',
    },
]


@attr.s
class Pipfile(object):

    sources = attr.ib()
    packages = attr.ib()
    dev_packages = attr.ib()
    requires = attr.ib()
    _data = attr.ib()

    @classmethod
    def from_data(cls, data):
        sources = [
            sections.Source.load(s)
            for s in data.pop("source", DEFAULT_SOURCES)
        ]
        requires = sections.Requires.load(data.pop("requires", {}))
        packages = {
            k: Requirement.from_pipfile(k, s)
            for k, s in data.pop("packages", {}).items()
        }
        dev_packages = {
            k: Requirement.from_pipfile(k, s)
            for k, s in data.pop("dev-packages", {}).items()
        }
        return cls(
            packages=packages, dev_packages=dev_packages,
            sources=sources, requires=requires, data=data,
        )

    @classmethod
    def load(cls, f, encoding=None):
        data = f.read()
        if encoding is not None:
            data = data.decode(encoding)
        data = tomlkit.loads(data)
        return cls.from_data(data)

    def __getitem__(self, key):
        return self._data[key]

    def get_hash(self):
        data = self.as_data()
        data = {
            "_meta": {
                "sources": data["source"],
                "requires": data["requires"],
            },
            "default": data["packages"],
            "develop": data["dev-packages"],
        }
        content = json.dumps(data, sort_keys=True, separators=(",", ":"))
        if isinstance(content, six.text_type):
            content = content.encode("utf-8")
        return hashlib.sha256(content)

    def as_data(self):
        data = {
            "source": [source.as_data() for source in self.sources],
            "packages": {
                k: v.as_pipfile()[k] for k, v in self.packages.items()
            },
            "dev-packages": {
                k: v.as_pipfile()[k] for k, v in self.dev_packages.items()
            },
            "requires": self.requires.as_data(),
        }
        data.update({
            k: tomlkit.loads(tomlkit.dumps(v))
            for k, v in self._data.items()
            if k not in data
        })
        return data

    def dump(self, f, encoding=None):
        data = tomlkit.dumps(self.as_data())
        if encoding is not None:
            data = data.encode(encoding)
        f.write(data)
