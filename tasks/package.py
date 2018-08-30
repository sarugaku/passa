import invoke


@invoke.task()
def pack(ctx):
    """Build a isolated runnable package.
    """
