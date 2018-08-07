import attr


@attr.s
class Lockfile(object):

    pipfile_spec = attr.ib()
    pipfile_hash = attr.ib()
    python_requirement = attr.ib()
    sources = attr.ib()
    default_requirements = attr.ib()
    develop_requirements = attr.ib()

    def as_dict(self):
        return {
            "_meta": {
                "hash": {
                    self.pipfile_hash.name: self.pipfile_hash.hexdigest(),
                },
                "pipfile-spec": self.pipfile_spec,
                "requires": self.python_requirement.as_dict(),
                "sources": [source.as_dict() for source in self.sources],
            },
            "default": self.default_requirements.as_dict(),
            "develop": self.develop_requirements.as_dict(),
        }
