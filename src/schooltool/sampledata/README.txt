===============================
Pluggable sample data framework
===============================

There are several goals to this framework:

- provide the developers with a SchoolTool setup that is close to
  real-world use in amounts of data in the database, so various
  performance and usability problems are noticed and taken care of
  early

- provide the users with an easy setup for evaluating SchoolTool with
  plausible data

The framework is pluggable and allows the creators of SchoolTool
extensions to provide their own plugins that generate sample data for
those extensions.


What data does it generate?
---------------------------

Currently, the framework generates a school with a 1000 students, 48
teachers, 64 rooms and 24 projectors, 240 sections of 24 courses,
sets up a 6 day 6 period rotating timetable schema, and sets up
timetables for all teachers and students.  All sections and people get
random events added to their calendars every now and then.


How to use it?
--------------

Sample data generation is available in the developer mode.  In order
to enable it, uncomment the `devmode on` line in your schooltool.conf.

You need to run the sample data generation with an empty database, so
most probably you need to remove the Data.fs file.  Start the
SchoolTool server, log in as `manager`, choose Sample Data from the
developer mode menu, change the random seed if you want to, and press
'Generate'.  Be patient, it takes several minutes even on fast machines.

When the generation is done, you'll get a summary of how much CPU time
each plugin took.  Unfortunately, generating this amount of data
imposes significant overhead, so the run time of the plugins does not
quite sum up to the amount of wall time the generation took.


How do I create a sample data plugin?
-------------------------------------

In order to create a sample data plugin, you only have to register a
named utility that implements the interface
`schooltool.sampledata.interfaces.ISampleDataPlugin`.  This interface
is very simple, it requires only the `name` attribute with the unique
name of the plugin, the `dependencies` attribute with names of plugins
this one depends on, and a `generate` method that generates its data
given that the dependencies have already been satisfied.

If your plugin depends on some objects, such as persons, groups,
courses, timetable setup, you can find out the names of the
appropriate plugins by looking at the source of the existing plugins
in these modules::

  schooltool.person.sampledata
  schooltool.group.sampledata
  schooltool.resource.sampledata
  schooltool.course.sampledata
  schooltool.timetable.sampledata


Crude example
-------------

Let's say you want to create a plugin that adds a 'favorite_color' annotation
to all persons, with randomly chosen values of 'red', 'green', or 'blue'.
Obviously, your plugin depends on teachers and students already being in the
database, so you will depend on plugins 'teachers' and 'students'.

You need to define a plugin::

  import random
  import zope.interface
  from zope.annotation.interfaces import IAnnotations
  from schooltool.sampledata.interfaces import ISampleDataPlugin
  from schooltool.sampledata import PortableRandom

  class PersonColorPlugin(object):
      zope.interface.implements(ISampleDataPlugin)
      name = 'person_color'
      dependencies = ('teachers', 'students')

      def generate(self, app, seed=None):
          rng = PortableRandom(seed)
          for person in app['persons'].values():
              color = rng.choice(['red', 'green', 'blue'])
              IAnnotations(person)['favorite_color'] = color

Now, you need to register it in your ``configure.zcml``.  You need to
conditionally include your registration of the sample data plugin for
the developer mode:

.. code-block:: xml

  <configure xmlns="http://namespaces.zope.org/zope">

    <!-- ... -->

    <configure
        xmlns:zcml="http://namespaces.zope.org/zcml"
        zcml:condition="have devmode">

      <utility
          factory=".PersonColorPlugin"
          provides="schooltool.sampledata.interfaces.ISampleDataPlugin"
          name="person_color"
          />

    </configure>

  </configure>

Voila!  Remove ``Data.fs``, regenerate sample data, and all your teachers
and students should know their colours!

