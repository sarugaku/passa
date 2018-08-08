# -*- coding=utf-8 -*-
import resolvelib


class Resolver(resolvelib.Resolver):
    def __init__(self, *args, **kwargs):
        super(Resolver, self).__init__(*args, **kwargs)
        self.criteria = {}

    def resolve(self, requirements, max_rounds=20):
        resolution = resolvelib.resolvers.Resolution(self.provider, self.reporter)
        resolution.resolve(requirements, max_rounds=max_rounds)
        self.criteria = resolution._criteria.copy()
        return resolution.state
