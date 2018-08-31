import invoke

from . import admin, package


def add_tasks(module, prefix=None):
    if prefix is None:
        prefix = module.__name__.rsplit('.', 1)[-1]
    child_namespace = invoke.Collection.from_module(module)
    for name in child_namespace.task_names:
        if name in namespace.task_names:
            raise ValueError('duplicate task {}'.format(name))
        namespace.add_task(child_namespace[name], name=name)


namespace = invoke.Collection()
add_tasks(admin)
add_tasks(package)
