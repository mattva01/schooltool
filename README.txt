SchoolTool
==========

SchoolTool - a common information systems platform for school administration.

Website: http://www.schooltool.org/

Mailing list: http://lists.schooltool.org/mailman/listinfo/schooltool

Bug tracker: http://issues.schooltool.org/


Default Login and Password
--------------------------

Username: manager
Password: schooltool

You should change the password after your first login by clicking on 'SchoolTool
Manager' in the top bar and then 'Edit Info' in the left sidebar.


Overview
--------

SchoolTool is an open source school management information system.  It is
a distributed client/server system.  The SchoolTool server presents two
interfaces to clients:

  - a traditional web application interface, usable with an ordinary browser.

  - HTTP-based programming interface suitable for fat clients, adhering to
    the Representational State Transfer (REST) architectural style (see
    http://rest.blueoxen.net/).

The web application interface is the primary one.  The RESTive interface is
there for potential interoperability with other systems and fat clients to
perform data entry that is inconvenient to do via the web application
interface.

There are several clients that demonstrate the usage of the REST interface
(a command-line client that is used for functional tests, a wxWidgets GUI
client, and a command-line client for data import).

Any modern web browser is suitable for the web application interface.  The
interface degrades gracefully, so a browser that does not support CSS or
Javascript will be usable, although perhaps not very nice or convenient.


System requirements
-------------------

- Python 2.4 (http://www.python.org/)
  (Debian users will need either python2.4 and python2.4-xml packages)

- Zope 3.2 (http://www.zope.org/Products/Zope3)

- libxml2 Python bindings (http://xmlsoft.org/).  Windows users can find
  binaries here:  http://users.skynet.be/sbi/libxml-python/

- the Python Imaging Library (PIL) (http://www.pythonware.com/products/pil/)

- (optional) the ReportLab Toolkit (http://www.reportlab.org), and
  Arial and Times New Roman TrueType fonts.  ReportLab is only needed if
  you want to generate PDF calendars.  To enable PDF support you will
  need to specify the path to fonts in the configuration file.

Building and installing SchoolTool from a source tarball
--------------------------------------------------------

From the un-packed tarball you can use the familiar ./configure; make;
make install dance. So, going through it:

$ ./configure --prefix=${libs}

where ${libs} is the location where you want to install the libraries
(it can be anywhere).

$ make
$ make install

Change directory to the installed libraries:

$ cd ${libs}

Now from the installed libraries, we can test the installation by running:

$ ./bin/schooltooltest -ufv1

Then create a schooltool instance (${instance} is the directory to create the
instance in):

$ ./bin/mkschooltoolinst -d${instance}

Change to the instance and test it:

$ cd ${instance}
$ ./bin/test -ufv --testschooltool

Then you can start the server:

$ ./bin/schooltool-server


Building SchoolTool from a subversion checkout
----------------------------------------------

Run 'make build update-translations' to build the necessary extension modules
and translations.  You will need to have gettext installed to compile the
translations.

It is a good idea to run 'make test' and 'make ftest' to check if all the
essential unit and functional tests pass.


Running SchoolTool
------------------

The top-level project directory contains the following executable Python
scripts:

  schooltool-server.py      starts the SchoolTool server

The SchoolTool server automatically creates an empty database if it cannot find
an existing one.  You can customize the location of the database and a few
other parameters in a configuration file called schooltool.conf.  There's
an example file called schooltool.conf.in, you can simply rename it and modify
to suit your needs.

Beware that the file which contains the database, Data.fs, is not given any
special permissions to prevent it from being read by other users by default.
You will have to change the umask or the permissions of the file manually to
prevent unauthorized access.

By default a user with manager privileges is created in the new database.
The username is 'manager', and the password is 'schooltool'.  The database
is otherwise mostly empty.

The default web application port is 7080.  Once the server is running, you can
connect to it with a web browser.


Project structure (subversion checkout only)
--------------------------------------------

  GPL                   the GNU General Public License, version 2
  README                this file
  RELEASE               release notes for the latest release

  Makefile              makefile for building extension modules
  setup.py              distutils setup script for building extension modules
  test.py               test runner
  remove-stale-bytecode.py
                        script to remove stale *.pyc files

  schooltool-server.py  script to start the SchoolTool server
  schooltool.conf.in    sample configuration file

  build/                temporary files are placed here during build process
  coverage/             unit test coverage reports (produced by make coverage)
    reports/            html version of the above (make coverage-reports-html)
  doc/                  documentation
  src/                  source code
    schooltool/         Python package 'schooltool'
      main.py           the SchoolTool server
      *.py              other modules (see docstrings)
      tests/            unit tests for the schooltool package
      browser/          web application views for the server
        resources/      resource files (images, stylesheets)
        templates/      page templates
        tests/          unit tests for the schooltool.browser package
      rest/             RESTive views for the server
        templates/      page templates
        tests/          unit tests for the schooltool.rest package
    schoolbell/         Python package 'schoolbell'


Testing
-------

There are two sets of automated tests: unit tests and functional tests.
Unit tests (sometimes also called programmer tests) test individual components
of the system.  Functional tests (also called customer or acceptance tests)
test only externally visible behaviour of the whole system.

Tests themselves are scattered through the whole source tree.  Subdirectories
named 'tests' contain unit tests, while subdirectories named 'ftests' contain
functional tests.

To run all unit tests, do

  python test.py -pv

To run all functional tests, do

  python test.py -fpv

The test runner has more options and features.  To find out about them, do

  python test.py -h


Unit test coverage
------------------

All code should be covered by unit tests.  The test runner can help you look
for untested code by producing code coverage reports.

To generate unit test coverage reports, run

  make coverage

This command will run the full SchoolTool unit test suite and produce a
number of files (one for each Python module) in ./coverage/.  Every
report file contains the source of the corresponding Python module.
Each source line is annotated with a number that shows how many times
this line was reached during testing.  Watch out for lines marked with
'>>>>>>' as they indicate code that is not unit tested.

A prettier HTML version of the coverage reports can be generated with

  make coverage
  make coverage-reports-html

Look at HTML files in ./coverage/reports/.  You should have enscript installed
for syntax highlighting source files.

The HTML version of coverage reports is published nightly at
http://source.schooltool.org/coverage/

There are some other helpful make targets:

  make coverage-report-list

    Lists all non-test modules from the schooltool package that contain
    untested code.

  make coverage-report

    Like 'make coverage-report-list', but is somewhat slower and also
    shows the number of untested lines in each module.

  make vi-coverage-reports

    Launches vi for all coverage reports listed by 'make
    coverage-report-list'.  Type />>>>>> to search for untested code,
    then type :next to look at the next report.

  make edit-coverage-reports

    Like 'make vi-coverage-reports' but uses $EDITOR rather than
    hardcoding 'vi'.


Translation
-----------

Translation files live in src/schooltool/locales.  There is a directory
for each language that contains a subdirectory called LC_MESSAGES that
contains two files: schooltool.po and schooltool.mo.

To start a new translation, create a language directory and LC_MESSAGES and
use src/schooltool/translation/schooltool.pot as a template.  Generate
schooltool.mo with msgfmt (or by calling make update-translations).

When you change the translatable strings in the source code or page templates,
be sure to run

  make extract-translations


Virtual hosting
---------------

SchoolTool provides support for virtual hosting with Apache's mod_rewrite.
For example, let's say you have two SchoolTool instances running on ports
7001 and 7002, and you want to make them available as school1.example.org
and school2.example.org, both on port 80.  In order to do that, add the
following to your Apache configuration file:

  NameVirtualHost *:80

  <VirtualHost *:80>
    ServerName school1.example.org
    RewriteEngine On
    RewriteRule ^/(.*) http://localhost:7001/++vh++http:school1.example.org:80/++/$1 [P]
  </VirtualHost>

  <VirtualHost *:80>
    ServerName school2.example.org
    RewriteEngine On
    RewriteRule ^/(.*) http://localhost:7002/++vh++http:school2.example.org:80/++/$1 [P]
  </VirtualHost>

Also, enable mod_proxy and mod_rewrite.

You can also get SSL support in the same way.

  NameVirtualHost *:443

  <VirtualHost *:443>
    ServerName school1.example.org
    SSLEnable          # Apache 1.3
    # SSLEngine On     # Apache 2.0
    RewriteEngine On
    RewriteRule ^/(.*) http://localhost:7001/++vh++https:school1.example.org:443/++/$1 [P]
  </VirtualHost>

The web application interface also supports virtual hosting in this manner,
the only differing thing would be the local port number.


Copyright information
---------------------

SchoolTool is copyright (c) 2003--2006 Shuttleworth Foundation

All files in the src/schooltool directory (with some exceptions in
src/schooltool/locales) are part of SchoolTool, and are (c) Shuttleworth
Foundation.

Unless otherwise stated, files in src/schooltool are released under the
terms of the GNU General Public License as published by the Free
Software Foundation; either version 2 of the License, or (at your option)
any later version.

Files in the same directory as this README file are (c) Shuttleworth
Foundation, with the exception of GPL, which is a copy of the Free Software
Foundation's General Public License, and is (c) FSF.


SchoolTool is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

You can find the full copy of the GNU General Public License in a file called
GPL in the project directory.
