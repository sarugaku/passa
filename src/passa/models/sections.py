import attr
import six


@attr.s
class Hash(object):
    # Attributes are defined to be compatible with hashlib's hash type.
    name = attr.ib()
    _hexdigest = attr.ib()

    def hexdigest(self):
        return self._hexdigest


@attr.s
class PythonRequirement(object):
    version = attr.ib()


class PythonVersionRequirement(PythonRequirement):
    def as_dict(self):
        return {"python_version": self.version}


class PythonFullVersionRequirement(PythonRequirement):
    def as_dict(self):
        return {"python_full_version": self.version}


@attr.s
class Source(object):

    name = attr.ib()
    url = attr.ib()
    verify_ssl = attr.ib()

    @classmethod
    def parse(cls, url):
        parts = six.moves.urllib.parse.urlsplit(url)
        secure = (parts.scheme == "https")  # XXX: Is this enough?
        return cls(name=parts.netloc, url=url, verify_ssl=secure)

    def as_dict(self):
        return {
            "name": self.name,
            "url": self.url,
            "verify_ssl": self.verify_ssl,
        }


@attr.s
class Candidate(object):

    ireq = attr.ib()
    hashes = attr.ib()
    dependencies = attr.ib()
