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

basedir = os.path.abspath(os.path.dirname(sys.argv[0]))
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
    ssl = False
    interactive = False

    expected_version = 'SchoolTool/0.8'

    datadir = datadir
    ttconfig_filename = datadir + '/ttconfig.data'

    def main(self, argv):
        """Generate and import sample school data."""
        self.real_stdout = sys.stdout
        sys.stdout = StreamWrapper(sys.stdout)
        sys.stderr = StreamWrapper(sys.stderr)
        try:
            self.process_args(argv)
            self.check_data_files()
            if self.interactive:
                self.input_settings()
            self.check_server_running()
            self.import_timetable_data()
            self.import_csv_files()
        except Error, e:
            print _("An error occured!")
            print >> sys.stderr, unicode(e)
            if self.interactive:
                print _("Press <Enter> to continue.")
                raw_input()
            return 1
        else:
            if self.interactive:
                print _("The sample school has been imported succesfully.")
                print _("Press <Enter> to continue.")
                raw_input()
            return 0

    def process_args(self, argv):
        """Process command line arguments."""
        try:
            opts, args = getopt.getopt(argv[1:], 'h:p:si',
                                       ['host=', 'port=', 'ssl', 'interactive'])
        except getopt.error, e:
            raise Error(e)

        for k, v in opts:
            if k in ('-h', '--host'):
                self.host = v
            elif k in ('-p', '--port'):
                try:
                    self.port = int(v)
                except ValueError, e:
                    raise Error(_("Invalid port number: %s") % v)
            elif k in ('-s', '--ssl'):
                self.ssl = True
            elif k in ('-i', '--interactive'):
                self.interactive = True

    def input_settings(self):
        """Interactively ask to type in the host and port."""
        while True:
            print _("Please enter the hostname of the server:"),
            host = raw_input().strip()
            if host:
                self.host = host
                break

        while True:
            print _("Please enter the port number:"),
            port = raw_input().strip()
            try:
                port = int(port)
            except ValueError:
                pass
            else:
                if port > 0 and port < 65536:
                    self.port = port
                    break

        while True:
            print _("Use SSL? (y/n)"),
            s = raw_input().strip().upper()
            if s == _('y').upper():
                self.ssl = True
                break
            elif s == _('n').upper():
                self.ssl = False
                break

    def check_data_files(self):
        """Check that the data files exist."""
        for filename in ('groups.csv', 'persons.csv',
                         'resources.csv', 'timetable.csv'):
            if not os.path.exists(os.path.join(self.datadir, filename)):
                raise Error(_("%s does not exist.  "
                              "Please run generate-sampleschool.py")
                            % filename)

    def check_server_running(self):
        """Check that the server is running, and it is the correct version."""
        if self.ssl:
            proto = 'https'
        else:
            proto = 'http'
        try:
            # urllib.urlopen uses FancyURLopener which is too fancy
            f = urllib.URLopener().open("%s://%s:%s"
                                        % (proto, self.host, self.port))
        except IOError:
            raise Error(_("SchoolTool server not listening on %s:%s")
                        % (self.host, self.port))
        else:
            version = f.info().getheader('Server')
            if version != self.expected_version:
                raise Error(_("Server version is %s, expected %s")
                            % (version, self.expected_version))

    def import_csv_files(self):
        """Import data from CSV files."""
        from schooltool.clients.csvclient import CSVImporterHTTP, DataError
        os.chdir(self.datadir)
        importer = CSVImporterHTTP(host=self.host, port=self.port,
                                   ssl=self.ssl)
        try:
            importer.run()
        except DataError, e:
            raise Error(e)

    def import_timetable_data(self):
        """Import timetable data from ttconfig.data."""
        import schooltool.clients.client
        ttconfig = file(self.ttconfig_filename)
        c = schooltool.clients.client.Client(stdin=ttconfig,
                                             stdout=self.real_stdout)
        c.use_rawinput = False
        c.input_hook = lambda prompt: ttconfig.readline()[:-1]
        c.server = self.host
        c.port = self.port
        c.ssl = self.ssl
        c.cmdloop()


if __name__ == '__main__':
    sys.exit(SampleSchoolImporter().main(sys.argv))
