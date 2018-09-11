==============
Passa’s Design
==============

Passa’s interface is modelled on Sam Boyer’s **Map, Sync, Memo** design, outlined in his blog piece `So you want to write a package manager`_. The terms are tweaked a little to prevent descrepencies to existing tools (i.e. Pipenv), but the ideas are generally the same.

.. _`So you want to write a package manager`: https://medium.com/@sdboyer/so-you-want-to-write-a-package-manager-4ae9c17d9527


Map, Sync, Memo
===============

In Map, Sync, Memo, a project’s dependency has four representations. Those four representations are, in terms of a Pipfile project:

* ``P`` — *Project code*, user code that depends on other code, and the abstract idea of that dependency.
* ``M`` — *Manifest*, a machine-understandable description of ``P``, i.e. ``packages`` and ``dev-packages`` sections in Pipfile.
* ``L`` — *Lock file**, a frozen set of actual package specifications that satisfies ``M``, i.e. package section in Pipfile.lock.
* ``D`` — *Dependency code*, things that are actually installed into the Python environment.

A package manager should strive to keep those four in sync. Three functions are required:

* ``f(P, M)`` is modification to Pipfile. The user specifies dependencides based on their understanding to ``P``. This could be automated by the package manager (e.g. a CLI to automatically add lines in Pipfile with the correct syntax), but the user should be responsible for Pipfile’s ultimate accuracy.
* ``f(M, L)`` takes Pipfile’s content, and *lock* its specifications into Pipfile.lock. This could also take additional cues from other sources, mainly an existing Pipfile.lock, to avoid unwanted package updates in the environment.
* ``f(L, D)`` takes specifications in Pipfile.lock, and actually install them into the environment. This may include a cleanup phase, in which *unspecified* packages are automatically uninstalled.

Notice that the synchonization is one-way, e.g. the environment shouldn’t be able to specify what should go into Pipfile.lock.


Top-Tier Operations
===================

A package manager should strive to keep the four representations in sync. When a modification is made to the manifest (Pipfile), it should trigger ``f(M, L)`` to update the lock file, and ``f(L, D)`` to synchronize the lock file into the environments. Commands :ref:`add <cmd-add>` and :ref:`remove <cmd-remove>` fall into this category.

A user may also choose to re-run the locking process without modifying Pipfile. This is generally run in a periotic fashion to know whether there are new versions available for dependencides of this project. This can be done with :ref:`upgrade <cmd-upgrade>`. This operation will also trigger ``f(L, D)``.

It is also possible to run ``f(L, D)`` by itself. This is most common for deployment or project cooperation: the lock file is generated on a machine, and when it is copied/checked out on another machine, the environment can be synchronized directly from it, without running the locking operation again, thus guarenteeing the dependencides are identical across environments. This can be done with :ref:`sync <cmd-sync>`. Note that this is different from Boyer’s terminology—he named this operation *install*, but Pipenv already uses it for another operation; *sync* is more in line with what we want to do.


Single-Step Operations
======================

The top-tier operations try their best to keep the representations in sync. Sometimes, however, the user may want to explicitly de-sync things. The single step operations allow for fine-grained tinkering to suit the user’s needs.

* ``f(P, M)`` does not have a strict equivalent, since the user can always edit the manifest by hand. Both :ref:`add <cmd-add>` and :ref:`remove <cmd-remove>`, however, offer a ``--no-sync`` flag to stop after ``f(M, L)`` (and preventing ``f(L, D)``). These are, in math notation, ``f(M, L) ∘ f(L, D)``.
* ``f(M, L)`` can be indivisually executed with :ref:`lock <cmd-lock>`.


Special Considerations
======================

There is one special operation :ref:`clean <cmd-clean>`. Python, unlike many other developing environments, does not usually have its application dependencies live in *complete* isolation. A Python environment often needs to contain additional packages, but the developer might not want to include them in Pipfile. Passa, therefore, allows you to *not* uninstall unlisted packages when you run :ref:`sync <cmd-sync>`, by specifying `--no-clean`, or to run :ref:`clean <cmd-clean>` by itself.

To accompany :ref:`clean <cmd-clean>`, it is sometimes desired to “fix” a temporarily state, where Pipfile.lock and the environment are out of sync. This is done by :ref:`install <cmd-install>`. This command is essentially “lock if contents of Pipfiel and Pipfile.lock don’t match, and then sync”. This allows for a way to guarentee you can synchronize Pipfile into your environment at any time, but avoid redundant locking (wasting time and resource) if possible.

Passa allows exporting the project’s Pipfile.lock into a `requirements.txt`_ compatible format, by running :ref:`freeze <cmd-freeze>`. This is similar to ``pip freeze``, but instead of freezing the content of the current environment, its output is based on Pipfile.lock.

.. _`requirements.txt`: https://pip.pypa.io/en/stable/user_guide/#id1
