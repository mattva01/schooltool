SchoolBell
==========

SchoolBell is a calendaring server that speaks WebDAV and has a traditional
browser application.  It is built on top of Zope 3 and uses the SchoolBell
calendaring library for Zope 3.

Installation
------------

This is an early development version of SchoolBell.  To get it running

1. Check out schooltool from source.schooltool.org
2. Go into the Zope 3 subdirectory
3. Copy sample_principals.zcml to principals.zcml
4. Copy zope.conf.in to zope.conf and add

      path ../src

5. Create a file named schoolbell-configure.zcml in package-includes/ with the
   following content:

      <include package="schooltool.sbapp" />

6. Start z3.py
7. Go to http://localhost:8080/@@manage, log in as 'gandalf' with
   password '123', add a SchoolBell instance from the menu on the left.
