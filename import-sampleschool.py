#!/usr/bin/env python
"""
A script to import sample school data into SchoolTool.
"""

import os
import sys

if sys.version_info < (2, 3):
    print >> sys.stderr, '%s: need Python 2.3 or later.' % sys.argv[0]
    print >> sys.stderr, 'Your python is %s' % sys.version
    sys.exit(1)

basedir = os.path.abspath(os.path.dirname(__file__))
datadir = basedir
sys.path.insert(0, os.path.join(basedir, 'src'))

# If you modify something above, take a look at debian/rules and
# debian/import-sampleschool.head, too.
# -- Do not remove this line --

import urllib
import getopt
from schooltool.common import StreamWrapper, UnicodeAwareException
from schooltool.translation import ugettext as _


class Error(UnicodeAwareException):
    pass


class SampleSchoolImporter:

    host = 'localhost'
    port = 7001

    expected_version = 'SchoolTool/0.5'

    datadir = datadir
    ttconfig_filename = datadir + '/ttconfig.data'

    def main(self, argv):
        """Generate and import sample school data."""
        sys.stdout = StreamWrapper(sys.stdout)
        sys.stderr = StreamWrapper(sys.stderr)
        try:
            self.process_args(argv)
            self.check_data_files()
            self.check_server_running()
            self.check_server_empty()
            self.import_csv_files()
            self.import_timetable_data()
        except Error, e:
            print >> sys.stderr, unicode(e)
            return 1
        else:
            return 0

    def process_args(self, argv):
        """Process command line arguments."""
        try:
            opts, args = getopt.getopt(argv[1:], 'h:p:', ['host=', 'port='])
        except getopt.error, e:
            raise Error(e)

        for k, v in opts:
            if k in ('-h', '--host'):
                self.host = v
            if k in ('-p', '--port'):
                try:
                    self.port = int(v)
                except ValueError, e:
                    raise Error(_("Invalid port number: %s") % v)

    def check_data_files(self):
        """Check that the data files exist."""
        for filename in ('groups.csv', 'pupils.csv', 'teachers.csv',
                         'resources.csv'):
            if not os.path.exists(os.path.join(self.datadir, filename)):
                raise Error(_("%s does not exist.  "
                              "Please run generate-sampleschool.py")
                            % filename)

    def check_server_running(self):
        """Check that the server is running, and it is the correct version."""
        try:
            # urllib.urlopen uses FancyURLopener which is too fancy
            f = urllib.URLopener().open("http://%s:%s"
                                        % (self.host, self.port))
        except IOError:
            raise Error(_("SchoolTool server not listening on %s:%s")
                        % (self.host, self.port))
        else:
            version = f.info().getheader('Server')
            if version != self.expected_version:
                raise Error(_("Server version is %s, expected %s")
                            % (version, self.expected_version))

    def check_server_empty(self):
        """Check that the server is running, and it is the correct version."""
        for path in '/groups/teachers', '/ttschemas/default':
            try:
                # urllib.urlopen uses FancyURLopener which is too fancy
                f = urllib.URLopener().open("http://%s:%s%s"
                                            % (self.host, self.port, path))
            except IOError:
                # good, we got a 404
                return
            else:
                raise Error(_("SchoolTool server already has data imported."
                              " Remove your Data.fs if necessary,\n"
                              "restart the server and try again."))

    def import_csv_files(self):
        """Import data from CSV files."""
        from schooltool.clients.csvclient import CSVImporter, DataError
        os.chdir(self.datadir)
        importer = CSVImporter(host=self.host, port=self.port)
        try:
            importer.run()
        except DataError, e:
            raise Error(e)

    def import_timetable_data(self):
        """Import timetable data from ttconfig.data."""
        import schooltool.clients.client
        ttconfig = file(self.ttconfig_filename)
        c = schooltool.clients.client.Client(stdin=ttconfig)
        c.use_rawinput = False
        c.input_hook = lambda prompt: ttconfig.readline()[:-1]
        c.server = self.host
        c.port = self.port
        c.cmdloop()


if __name__ == '__main__':
    sys.exit(SampleSchoolImporter().main(sys.argv))
