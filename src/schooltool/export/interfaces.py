#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2012 Shuttleworth Foundation
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

import zope.schema
import zope.file.interfaces
from zope.publisher.interfaces.browser import IBrowserPage

from schooltool.report.interfaces import IReportMessage
from schooltool.report.interfaces import IReportFile
from schooltool.task.interfaces import IProgressMessage
from schooltool.task.interfaces import IRemoteTask

from schooltool.common import SchoolToolMessage as _


class IXLSExportView(IBrowserPage):

    filename = zope.schema.TextLine(
        title=u"XLS file name", required=False)

    render_invariant = zope.schema.Bool(
        title=u"Render invariant",
        description=u"Render without influence form environment, like current time.",
        required=False)

    render_debug = zope.schema.Bool(
        title=u"Render debug",
        description=u"Render with debug information.",
        required=False)


class IXLSProgressMessage(IProgressMessage, IReportMessage):
    pass


class IImportFile(IReportFile):
    pass


class IImporterTask(IRemoteTask):

    xls_file = zope.schema.Object(
        title=_("XLS File"),
        schema=IImportFile)
