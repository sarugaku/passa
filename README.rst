===============================================================================
passa: A resolver implementation for generating and interacting with Pipenv-compatible Lockfiles.
===============================================================================

.. image:: https://img.shields.io/pypi/v/passa.svg
    :target: https://pypi.python.org/pypi/passa

.. image:: https://img.shields.io/pypi/l/passa.svg
    :target: https://pypi.python.org/pypi/passa

.. image:: https://travis-ci.org/sarugaku/passa.svg?branch=master
    :target: https://travis-ci.org/sarugaku/passa

.. image:: https://img.shields.io/pypi/pyversions/passa.svg
    :target: https://pypi.python.org/pypi/passa

.. image:: https://img.shields.io/badge/Say%20Thanks-!-1EAEDB.svg
    :target: https://saythanks.io/to/techalchemy

.. image:: https://readthedocs.org/projects/passa/badge/?version=master
    :target: http://passa.readthedocs.io/en/master/?badge=master
    :alt: Documentation Status


Installation
*************

Install from `PyPI`_:

  ::

    $ pipenv install --pre passa

Install from `Github`_:

  ::

    $ pipenv install -e git+https://github.com/sarugaku/passa.git#egg=passa


.. _PyPI: https://www.pypi.org/project/passa
.. _Github: https://github.com/sarugaku/passa


.. _`Summary`:

Summary
********

**Passa** is a resolver layer which is designed for performing dependency resolution using a
stateful backtracking algorithm to resolve dependency conflicts gracefully and with minimal 
intervention.  It is implemented using the directed acyclic graph built in `resolvelib`_. 
**Passa** is intended to operate on a `Pipfile`_ in order to produce a Lockfile in a valid
state.  It was designed to be used as the backing resolver for `pipenv`_ and is built on
top of elements from `requirementslib`_, the current interface layer between pipenv's
requirements and its internals.

.. _pipenv: https://github.com/pypa/pipenv
.. _pipfile: https://github.com/sarugaku/pipfile
.. _resolvelib: https://github.com/sarugaku/resolvelib
.. _requirementslib: https://github.com/sarugaku/requirementslib


.. _`Usage`:

Usage
******

Loading a *pipfile*
///////////////////////

You can use passa to import your **pipfile** and resolve its dependencies:

  ::

    import passa
    pipfile = passa.load('/path/to/project/dir/or/Pipfile')
    lockfile = passa.resolve(pipfile)
    lockfile.create()
