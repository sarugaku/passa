===================================
Passa: Toolset for Pipfile projects
===================================

Passa is a toolset for performing tasks in a Pipfile project. It contains
several components:

* A resolver designed for performing dependency resolution using a stateful
  look-forward algorithm to resolve dependencies (backed by ResolveLib_).
* Interface to interact with individual requirement specifications inside
  Pipfile and Pipfile.lock (backed by RequirementsLib_).
* A command line interface to invoke the above operations.

.. _ResolveLib: https://github.com/sarugaku/resolvelib
.. _RequirementsLib: https://github.com/sarugaku/requirementslib


Quickstart
==========

Install Passa with pip:

.. code-block:: none

    pip install passa

Use Passa to generate Pipfile.lock from the Pipfile in the current directory:

.. code-block:: none

    python -m passa lock

Add packages to the project:

.. code-block:: none

    python -m passa add pytz requests tqdm

Remove packages from the project:

.. code-block:: none

    python -m passa remove pytz

Generate requirements.txt for the current project:

.. code-block:: none

    python -m passa freeze --target requirements.txt
