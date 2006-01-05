========================================
The Commendation Package (Documentation)
========================================

The prime purpose of this package is to document the implementation of an
additional content component in SchoolTool. To motivate the documentation, Tom
Hoffman, the SchoolTool project manager, will act as the customer for this
extension, and the protagonist of the writing is the developer fulfilling the
customer's specifications.

Here is the original E-mail that contains Tom's specifications:

  I think for our sample product documentation, the opposite of our
  discipline referral system might be simple enough, that is, a
  commendation system (since no workflow is necessary).

  The overall idea is to allow teachers, clerks and administrators to
  enter a commendation for a person or group (including sections).

  Commendations are, by definition, public.

  Commendations have the following fields:

  * Scope: [group, school-wide, community, state, national, global]
  * Grantor
  * Title
  * Description
  * Date

  Users with the proper role should have an "Add commendation" action
  when they're viewing a person or group.

  If a user or group has a commendation, a "View commendations" action
  should be visible.

  For the school, a "View commendations" action should present a
  batched/searchable list of all commendations in reverse chronological
  order.

Thus, this documentation package will implement a simple commendation
system. To make the documentation more readible, it is split into four
sections as outlined below.


Outline
-------

1. Development of the ``Commendation`` Component

   [``BasicComponent.txt``]

   (a) Creating the Package
   (b) Development of the ``ICommendation`` Interface
   (c) Implementation of the ``Commendation`` Component
   (d) Testing the Implementation

2. Python-Integration of Commendations into SchoolTool

   [``PythonIntegration.txt``]

   (a) The ``Commendations`` container
   (b) Asoociating Commendations with SchoolTool Components

3. System-Integration of Commentations into SchoolTool

   [``SystemIntegration.txt``]

   (a) ZCML Registration of new Components
   (b) Create an Add and Commendations View
   (c) Testing Browser UI Code

4. Viewing the Commendations

   [``Viewing.txt``]

   (a) Caching Commendations
   (b) Searching Commendations
   (c) School-wide Commendations Overview


Using this Tutorial
-------------------

You may find the structure of this tutorial to be unusual.  Most of the
developer documentation in the SchoolTool and Zope 3 source code is in the
form of Python "doctests," and one purpose of this package is to give you
an introduction to reading and using documentation in this style.

The main narrative documentation is contained in text files, which are
formatted using a simple, unobtrusive markup language called `ReStructured
Text`__.  You can read the raw text files without much trouble, or they can
also easily be more prettily rendered as HTML, PDF or another format.

__ http://docutils.sourceforge.net/rst.html

Included in the narrative text, you will also see examples in the form of
simulated Python interpreter sessions.  If we wanted to demonstrate
addition, we could say:

  >>> 2+3
  5

In addition to being a demonstration which the reader can follow along and
experiment with in their own Python interpreter, these snippets also function
as real tests of the behavior of the tested components.  That is, when you run
the SchoolTool testrunner on this package, the testrunner will input ``2+3``
into its own virtual Python interpreter, and if the result it gets back is
not equal to the one listed, i.e., '5', then this will count as a failed test.
This will help us ensure that this documentation always works with the current
version of SchoolTool.  It is also an easy way for developers to write
tests.

To get the most out of this tutorial, you will need to refer back and forth
between these narrative files and the source code itself.  You also should
have an instance of SchoolTool running with this package installed.  Further
documentation and references are available via your SchoolTool server, if you
switch it into 'devmode.'  In your ``schooltool.conf`` file include a line
which says "devmode on."  This will add a drop-down menu in the upper right
hand corner of the page which gives you access to further SchoolTool and
Zope 3 docs.
