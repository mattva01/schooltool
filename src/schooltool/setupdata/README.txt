====================================================
Pluggable school setup data framework for SchoolTool
====================================================

The goal of this framework is to facilitate the automation of the 
initial setup of a school.  Schools are complex, and if the sys admin
is importing large bodies of archived data from legacy systems, mistakes, 
dead ends and false starts are practically inevitable, particularly while 
SchoolTool itself is new and rapidly evolving.  By scripting this process, 
the sys admin can easily make changes and rebuild the entire database from
scratch.

This system is intended to be implemented using customized Python scripts
to parse the school's legacy data.

The framework is based very closely (i.e., almost entirely copied from) 
SchoolTool's sample data framework.


How to use it?
--------------

School data setup is available in the developer mode.  In order
to enable it, uncomment the `devmode on` line in your schooltool.conf.
If you only have schooltool.conf.in, copy it to schooltool.conf and
then edit it.

Initially, the assumption is that you are doing this on an empty database.

When the generation is done, you'll get a summary of how much CPU time
each plugin took.  Unfortunately, generating this amount of data
imposes significant overhead, so the run time of the plugins does not
quite sum up to the amount of wall time the generation took.


How do I create a setup data plugin?
-------------------------------------

In order to create a school setup data plugin, you only have to register a
named utility that implements the interface
`schooltool.setupdata.interfaces.ISetupDataPlugin`.  This interface
is very simple, it requires only the `name` attribute with the unique
name of the plugin, the `dependencies` attribute with names of plugins
this one depends on, and a `generate` method that parses and returns
its data given that the dependencies have already been satisfied.

In practice, you want to create a package that corresponds to the school you're setting up.  It is convenient to just put it in src with everything else.  You'll need to put the appropriate snippet of ZCML in package-includes to point Zope to your school's setup package.  You'll also need to create a directory somewhere that Zope'll be able to find it that will contain your CSV files or whatever else you're pulling your data from.  

Then you can pretty much follow the instructions in the sampledata README, except instead of generating random data you're pulling it from a text file, or just hardwiring it into a script.