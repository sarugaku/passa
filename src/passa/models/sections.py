import attr
import six


@attr.s
class Hash(object):

    name = attr.ib()
    value = attr.ib()

    @classmethod
    def parse(cls, value):
        try:
            name, value = value.split(":", 1)
        except ValueError:
            name = "sha256"
        return cls(name=name, value=value)

    def hexdigest(self):    # Compatibility to hashlib.
        return self.value

    def as_line(self):      # Compatibility to requirementslib.
        return "{}:{}".format(self.name, self.value)


@attr.s
class RequiresPythonVersion(object):

    value = attr.ib()
    full = attr.ib()

    @classmethod
    def load(cls, data):
        if "python_full_version" in data:
            value = data["python_full_version"]
            full = True
        elif "python_version" in data:
            value = data["python_version"]
            full = False
        else:
            value = None
            full = False
        return cls(value=value, full=full)

    def as_data(self):
        if self.value is None:
            return {}
        key = "python_full_version" if self.full else "python_version"
        return {key: self.value}

    def copy(self):
        return RequiresPythonVersion(value=self.value, full=self.full)


@attr.s
class Requires(object):

    python_version = attr.ib()

    @classmethod
    def load(cls, data):
        return cls(python_version=RequiresPythonVersion.load(data))

    def as_data(self):
        data = {}
        data.update(self.python_version.as_data())
        return data

    def copy(self):
        return Requires(python_version=self.python_version.copy())


@attr.s
class Source(object):

    name = attr.ib()
    url = attr.ib()
    verify_ssl = attr.ib()

    @classmethod
    def load(cls, data):
        url = data["url"]
        verify_ssl = bool(data.get("verify_ssl", True))
        try:
            name = data["name"]
        except KeyError:
            name = six.moves.urllib.parse.urlsplit(url).netloc
        return cls(name=name, url=url, verify_ssl=verify_ssl)

    def as_data(self):
        return {
            "name": self.name,
            "url": self.url,
            "verify_ssl": self.verify_ssl,
        }

    def copy(self):
        return Source(name=self.name, url=self.url, verify_ssl=self.verify_ssl)
