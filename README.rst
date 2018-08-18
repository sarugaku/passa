===================================================
Passa: Resolver implementation for Pipfile projects
===================================================

.. image:: https://img.shields.io/pypi/v/passa.svg
    :target: https://pypi.python.org/pypi/passa

.. image:: https://img.shields.io/pypi/l/passa.svg
    :target: https://pypi.python.org/pypi/passa

.. image:: https://api.travis-ci.com/sarugaku/passa.svg?branch=master
    :target: https://travis-ci.com/sarugaku/passa

.. image:: https://img.shields.io/pypi/pyversions/passa.svg
    :target: https://pypi.python.org/pypi/passa

.. image:: https://img.shields.io/badge/Say%20Thanks-!-1EAEDB.svg
    :target: https://saythanks.io/to/techalchemy

.. image:: https://readthedocs.org/projects/passa/badge/?version=master
    :target: http://passa.readthedocs.io/en/master/?badge=master
    :alt: Documentation Status


Installation
============

Install from PyPI_::

    $ pipenv install --pre passa

Install from GitHub_::

    $ pipenv install -e git+https://github.com/sarugaku/passa.git#egg=passa


.. _PyPI: https://www.pypi.org/project/passa
.. _GitHub: https://github.com/sarugaku/passa



.. _Summary:

Summary
=======

**Passa** is a resolver layer which is designed for performing dependency
resolution using a stateful backtracking algorithm to resolve dependency
conflicts gracefully and with minimal intervention.  It is implemented using
the directed acyclic graph built in resolvelib_. **Passa** is intended to
operate on a Pipfile_ in order to produce a Lockfile in a valid state.  It
was designed to be used as the backing resolver for Pipenv_ and is built on
top of elements from requirementslib_, the current interface layer between Pipenv's requirements and its internals.

.. _Pipenv: https://github.com/pypa/pipenv
.. _pipfile: https://github.com/sarugaku/pipfile
.. _resolvelib: https://github.com/sarugaku/resolvelib
.. _requirementslib: https://github.com/sarugaku/requirementslib



.. _Usage:

Usage
=====

Loading a *Pipfile*
-------------------

You can use Passa to import your **Pipfile** project, and resolve its
dependencies::

    pipenv run python -m passa path/to/project

Pass the `--output` flag to control how the lock file is outputed. Possible
values are `print` (the default, prints to stdout), `write` (write to
Pipfile.lock in the project root), and `none` (suppress the output).
