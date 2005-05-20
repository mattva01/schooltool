#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2005 Shuttleworth Foundation
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
Classes for csv importing.

$Id$
"""

from zope.app.publisher.browser import BrowserView
from zope.security.proxy import removeSecurityProxy

from schoolbell import SchoolBellMessageID as _
from schoolbell.app.interfaces import ISchoolBellApplication
from schoolbell.app.app import SimpleNameChooser
from schoolbell.app.app import Group, Resource, Person

import csv

class BaseCSVImportView(BrowserView):

    __used_for__ = ISchoolBellApplication

    def __init__(self, context, request):
        BrowserView.__init__(self, context, request)
        self.errors = []
        self.success = []

    def update(self):
        if "UPDATE_SUBMIT" not in self.request:
            return

        charset = self.getCharset()
        if charset is None:
            return

        csvfile = self.request.get('csvfile', '')
        if csvfile:
            csvfile = csvfile.read()

        csvtext = self.request.get('csvtext', '')

        if not csvfile and not csvtext:
            self.errors.append(_('No data provided'))
            return

        if csvfile:
            try:
                unicode(csvfile, charset)
            except UnicodeError:
                self.errors.append(_('Could not convert data to Unicode'
                                     ' (incorrect charset?).'))
                return

        self.importer = self.importer_class(self.context, charset)
        ok = True
        if csvfile:
            ok = self.importer.importFromCSV(csvfile)
            if ok:
                self.success.append(_("CSV file imported successfully."))
            else:
                self.errors.append(_("Failed to import CSV file"))
                self._presentErrors(self.importer.errors)

        ok = True
        if csvtext:
            self.importer.charset = None
            ok = self.importer.importFromCSV(csvtext)
            if ok:
                self.success.append(_("CSV text imported successfully."))
            else:
                self.errors.append(_("Failed to import CSV text"))
                self._presentErrors(self.importer.errors)

    def _presentErrors(self, err):
        """Add any errors in our ErrorCollection to the view errors.
        """
        if err.generic:
            self.errors.extend(err.generic)

        if err.fields:
            self.errors.extend(err.fields)

    def getCharset(self):
        """Return the charset (as a string) that was specified in the request.

        Updates self.errors and returns None if the charset was not specified
        or if it is invalid.
        """
        charset = self.request['charset']
        if charset == 'other':
            charset = self.request['other_charset']
        if not charset:
            self.errors.append(_("No charset specified"))
            return
        try:
            unicode(' ', charset)
        except LookupError:
            self.errors.append(_("Unknown charset"))
            return
        return charset


class BaseCSVImporter(object):
    """A base class for CSV parsers and importers.

    Subclasses should define the createAndAdd method.
    """

    def __init__(self, container, charset=None):
        self.container = container
        self.errors = ImportErrorCollection()
        self.charset = charset
        self.cache = {}

    def parseCSVRows(self, rows):
        """Parse rows (a list of strings) in CSV format.

        Returns a list of rows as lists.

        rows must be in the encoding specified during construction of
        BaseCSVImportView; the returned values are in unicode.

        If the provided data is invalid, self.errors.generic will be updated
        and None will be returned.
        """
        result = []
        reader = csv.reader(rows)
        line = 0
        try:
            while True:
                line += 1
                values = [v.strip() for v in reader.next()]
                if self.charset:
                    values = [unicode(v, self.charset) for v in values]
                # Remove trailing empty cells.
                while values and not values[-1].strip():
                    del values[-1]
                result.append(values)
        except StopIteration:
            return result
        except csv.Error:
            error_msg = _("Error in CSV data, line ${line_no}")
            error_msg.mapping = {'line_no': line}
            self.errors.generic.append(error_msg)
        except UnicodeError:
            error_msg = _("Conversion to unicode failed in line ${line_no}")
            error_msg.mapping = {'line_no': line}
            self.errors.generic.append(error_msg)

    def importFromCSV(self, csvdata):
        """Import objects from CSV data.

        Should not throw exceptions, but will set self.*error attributes.
        Returns True on success.  If False is returned, it means that at least
        one of attributes of self.errors have been set, and that no changes to
        the database have been applied.
        """
        rows = self.parseCSVRows(csvdata.splitlines())
        if rows is None:
            return False

        for dry_run in [True, False]:

            for rowdata in rows:
                self.createAndAdd(rowdata, dry_run)

            if self.errors.anyErrors():
                assert dry_run, ("Something bad happened,"
                                 " aborting transaction.") # XXX
                return False

        return True

    def createAndAdd(self, obj, dry_run=True):
        """Create object and add to container.

        If dry_run is True, don't actually do anything, just validate the data.

        This should be defined in the subclass.
        """
        raise NotImplementedError("Please override this method in subclasses")


class ImportErrorCollection(object):
    """A simple container for import errors.

    This class just holds errors that occur in the CSVImporter class so they
    can be dealt with by the CSVImportView class.
    """

    def __init__(self):
        self.generic = []
        self.fields = []

    def anyErrors(self):
        return bool(self.generic or self.fields)

    def __repr__(self):
        return "<%s %r>" % (self.__class__.__name__, self.__dict__)


class SimpleCSVImporter(BaseCSVImporter):
    """A simple "title, description" csv importer.

    This class is only useful for CSV importers with required titles and
    optional descriptions (at the moment this only applies to Group and
    Resource importers).

    Subclasses must provide the following attributes.

        `factory` -- class to create an instance to add to the container
    """

    factory = None

    def __init__(self, container, charset=None):
        BaseCSVImporter.__init__(self, container, charset)
        self.container = container
        self.chooser = SimpleNameChooser(container)

    def createAndAdd(self, data, dry_run=True):
        """Create objects and add them to the container.
        """
        if not self.factory:
            raise NotImplementedError("factory attribute not defined in subclass")
        if len(data) < 1:
            self.errors.fields.append(_('Insufficient data provided.'))
            return

        if not data[0]:
            self.errors.fields.append(_('Titles may not be empty'))
            return

        if len(data) > 1:
            description = data[1]
        else: 
            description = ''

        obj = self.factory(title=data[0], description=description)
        name = self.chooser.chooseName('', obj)
        if not dry_run:
            self.container[name] = obj


class GroupCSVImporter(SimpleCSVImporter):
    """Group CSV Importer"""
    factory = Group


class ResourceCSVImporter(SimpleCSVImporter):
    """Resource CSV Importer"""
    factory = Resource


class PersonCSVImporter(BaseCSVImporter):
    """A Person CSV importer."""

    def __init__(self, container, charset=None):
        BaseCSVImporter.__init__(self, container, charset)
        self.container = container
        self.chooser = SimpleNameChooser(container)

    def createAndAdd(self, data, dry_run=True):
        """Create Person object and add to container.

        We are requiring that we have a username and fullname (title) set.  If
        any duplicates are found then an error is reported and the duplicate
        entries are reported back to the user.
        """
        if len(data) < 2:
            self.errors.fields.append(_("""Insufficient data provided."""))
            return

        if not data[0]:
            self.errors.fields.append(_('username may not be empty'))
            return

        if not data[1]:
            self.errors.fields.append(_('fullname may not be empty'))
            return

        username = data[0]
        fullname = data[1]
        if len(data) > 2:
            password = data[2]
        else: 
            password = None

        if username in self.container:
            error_msg = _("Duplicate username: ${username}")
            error_msg.mapping = {'username' : ', '.join(data)}
            self.errors.fields.append(error_msg)
            return

        obj = Person(username=data[0], title=data[1])

        if password:
            obj.setPassword(password)

        if not dry_run:
            self.container[data[0]] = obj


class GroupCSVImportView(BaseCSVImportView):
    """View for Group CSV importer."""

    def __init__(self, context, request):
        BaseCSVImportView.__init__(self, context, request)
        self.importer_class = GroupCSVImporter


class ResourceCSVImportView(BaseCSVImportView):
    """View for Resource CSV importer."""

    def __init__(self, context, request):
        BaseCSVImportView.__init__(self, context, request)
        self.importer_class = ResourceCSVImporter


class PersonCSVImportView(BaseCSVImportView):
    """View for Person CSV importer."""

    def __init__(self, context, request):
        BaseCSVImportView.__init__(self, context, request)
        self.importer_class = PersonCSVImporter


