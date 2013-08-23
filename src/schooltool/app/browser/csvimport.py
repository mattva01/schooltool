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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
SchoolTool application views.
"""
import csv
import transaction

from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.publisher.browser import BrowserView

import schooltool.skin.flourish.page
from schooltool.common import SchoolToolMessage as _
from schooltool.app.app import SimpleNameChooser
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.skin import flourish


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


class BaseCSVImportView(BrowserView):

    __used_for__ = ISchoolToolApplication

    def __init__(self, context, request):
        BrowserView.__init__(self, context, request)
        self.errors = []
        self.success = []

    def nextURL(self):
        return None

    @property
    def mode(self):
        mode = self.request.get('csv-input-mode')
        if (not mode and
            not self.request.get('csvfile') and
            self.request.get('csvtext')):
            return 'text'
        return mode or 'upload'

    def update(self):
        if "UPDATE_SUBMIT" not in self.request:
            return

        charset = self.getCharset()
        if charset is None:
            return

        csvfile = self.request.get('csvfile', '')
        if csvfile:
            csvfile = csvfile.read()

        csvtext = self.request.get('csvtext', '').strip()

        mode = self.mode

        if (mode == 'upload' and not csvfile or
            mode == 'text' and not csvtext):
            self.errors.append(_('No data provided'))
            return

        if mode == 'upload' and csvfile:
            try:
                unicode(csvfile, charset)
            except UnicodeError:
                self.errors.append(_('Could not convert data to Unicode'
                                     ' (incorrect charset?).'))
                return

        self.importer = self.importer_class(self.context, charset)
        ok = True

        if mode == 'upload':
            ok = self.importer.importFromCSV(csvfile)
            if ok:
                self.success.append(_("CSV file imported successfully."))
            else:
                self.errors.append(_("Failed to import CSV file"))
                self._presentErrors(self.importer.errors)
        elif mode == 'text':
            self.csvtext = csvtext
            default_charset = "utf-8"
            self.importer.charset = default_charset
            ok = self.importer.importFromCSV(csvtext.encode(default_charset))
            if ok:
                self.success.append(_("CSV text imported successfully."))
            else:
                self.errors.append(_("Failed to import CSV text"))
                self._presentErrors(self.importer.errors)

        if self.success:
            next_url = self.nextURL()
            if next_url:
                self.request.response.redirect(next_url)

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


class FlourishBaseCSVImportView(flourish.page.Page, BaseCSVImportView):
    content_template = ViewPageTemplateFile('templates/f_csvimport.pt')
    __init__ = BaseCSVImportView.__init__
    update = BaseCSVImportView.update

    def update(self):
        if "UPDATE_CANCEL" in self.request:
            self.request.response.redirect(self.nextURL())
            return
        return BaseCSVImportView.update(self)


class BaseCSVImporter(object):
    """A base class for CSV parsers and importers.

    Subclasses should define the createAndAdd method.
    """

    def __init__(self, container, charset=None):
        self.container = container
        self.errors = ImportErrorCollection()
        self.charset = charset
        self.chooser = SimpleNameChooser(container)

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
            error_msg = _("Error in CSV data, line ${line_no}",
                          mapping={'line_no': line})
            self.errors.generic.append(error_msg)
        except UnicodeError:
            error_msg = _("Conversion to unicode failed in line ${line_no}",
                          mapping={'line_no': line})
            self.errors.generic.append(error_msg)

    def importFromCSV(self, csvdata):
        """Import objects from CSV data.

        Should not throw exceptions, but will set self.*error attributes.
        Returns True on success.  If False is returned, it means that at least
        one of attributes of self.errors have been set, and that no changes to
        the database have been applied.
        """
        rows = self.parseCSVRows(csvdata.strip().splitlines())
        if rows is None:
            return False

        for dry_run in [True, False]:
            savepoint = transaction.savepoint()
            for rowdata in rows:
                self.createAndAdd(rowdata, dry_run)

            if self.errors.anyErrors():
                savepoint.rollback()
                return False

        return True

    def createAndAdd(self, obj, dry_run=True):
        """Create object and add to container.

        If dry_run is True, don't actually do anything, just validate the data.

        This should be defined in the subclass.
        """
        raise NotImplementedError("Please override this method in subclasses")


