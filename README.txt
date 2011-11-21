SchoolTool
==========

SchoolTool - a common information systems platform for school administration.

Website: http://www.schooltool.org/

Mailing list: https://launchpad.net/~schooltoolers

Bug tracker: http://bugs.launchpad.net/schooltool


Default Login and Password
--------------------------

Username: manager
Password: schooltool

You should change the password after your first login by clicking on 'SchoolTool
Manager' in the top bar and then 'Edit Info' in the left sidebar.


Overview
--------

SchoolTool is an open source school management information system.  It is
a web application, usable with an ordinary browser.

Any modern web browser is suitable for the web application interface.  The
interface degrades gracefully, so a browser that does not support CSS or
Javascript will be usable, although perhaps not very nice or convenient.


System requirements
-------------------

- Python (http://www.python.org/)

- libicu-dev: International Components for Unicode libraries (http://icu.sourceforge.net/download/)

- the Python Imaging Library (PIL) (http://www.pythonware.com/products/pil/)

- (optional) the ReportLab Toolkit (http://www.reportlab.org), and
  Liberation TrueType fonts.  ReportLab is only needed if you want to
  generate PDF reports and calendars.  To enable PDF support you will
  need to specify the path to fonts in the configuration file.


Building and running SchoolTool from a source tarball
-----------------------------------------------------

You need the basic C development tools:

$ sudo apt-get install build-essential

You need the Python development libraries:

$ sudo apt-get install python-dev python-profiler

You need this unicode library:

$ sudo apt-get install libicu-dev

You also need the python imaging library:

$ sudo apt-get install python-imaging

Optional: For pdf generation to work, you need to install fonts:

$ sudo apt-get install ttf-liberation

Run make to download and install all the required zope packages into
the eggs folder:

$ make

Now test the installation by running:

$ make test ftest

Create a fresh instance:

$ make instance

The instance is created in instance directory. If you want to,
edit instance/schooltool.conf and uncomment the line
that says devmode on. This allows you to add sample data, view the
online docs and other useful things. You don't want to leave this on
for a production server, however.

Start your server:

$ make run

Go to http://localhost:7080 to see your new server in action.


Building SchoolTool from a checkout
----------------------------------------------

Run 'make compile-translations' to build the necessary extension modules and
translations.  You will need to have gettext installed to compile the
translations.

It is a good idea to run 'make test' and 'make ftest' to check if all the
essential unit and functional tests pass.


Running SchoolTool
------------------

Run 'make run'

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


Project structure (checkout only)
--------------------------------------------

  GPL.txt               the GNU General Public License, version 2
  README.txt            this file
  CHANGES.txt           release notes for the latest release

  Makefile              makefile for building extension modules
  setup.py              distutils setup script for building extension modules

  build/                temporary files are placed here during build process
  coverage/             unit test coverage reports (produced by make coverage)
    reports/            html version of the above (make coverage-reports-html)
  doc/                  documentation
  src/                  source code
    schooltool/         Python package 'schooltool'


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

  python test.py -pv -u

To run all functional tests, do

  python test.py -pv -f

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


Translation
-----------

Translation templates live in src/schooltool/locales/*.pot, they are the
translatable strings extracted from the source. Translation templates are used
to update other translations and create new ones. You can generate them via
this command:

  $ make extract-translations

Translation files live in src/schooltool/locales.  There is a
directory for each language that contains a subdirectory called
LC_MESSAGES that contains the compiled .mo files.
The .mo files must be present if schooltool is to use them and are
built by the command:

  $ make compile-translations

To start a new translation, use src/schooltool/locales/schooltool.pot as a
template (copy it to YOUR_LANG.po).  Generate .mo files with msgfmt (or by
calling make compile-translations).


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

SchoolTool is copyright (c) 2003-2011 Shuttleworth Foundation

All files in the src/schooltool directory are part of SchoolTool, and
are (c) Shuttleworth Foundation, with the exception of translations in
src/schooltool/locales, which are under the copyright of their
original contributors via Launchpad at http://launchpad.net .

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
