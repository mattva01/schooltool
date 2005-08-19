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
Student Academic Record View

$Id: app.py 3481 2005-04-21 15:28:29Z bskahan $
"""
import zope.security
import zope.wfmc
from zope.app import form
from zope.app import zapi
from zope.app.publisher import browser

from schooltool.app import app
from schooltool import SchoolToolMessageID as _
from schooltool.level import interfaces
from schooltool.level.browser import promotion


class AcademicRecordView(browser.BrowserView):
    """Student's academic record."""

    def __init__(self, context, request):
        super(AcademicRecordView, self).__init__(context, request)
        self.record = interfaces.IAcademicRecord(context)

        # Create a status widget
        form.utility.setUpWidget(self, 'status',
                                 interfaces.IAcademicRecord['status'],
                                 form.interfaces.IInputWidget,
                                 value=self.record.status)
        # The macros used require a list of widgets to be available.
        self.widgets = (self.status_widget,)


    def updateStatus(self):
        """Update the status field in the academic record."""
        if 'UPDATE_SUBMIT' in self.request:
            self.record.status = self.status_widget.getInputValue()
            return _('The status was successfully updated.')


    def updateProcess(self):
        """Update the workflow process."""
        if 'INITIALIZE_SUBMIT' in self.request:
            pd = zapi.getUtility(zope.wfmc.interfaces.IProcessDefinition,
                                 name='schooltool.promotion')
            process = pd()
            process.start(zope.security.proxy.removeSecurityProxy(self.context),
                          None, None)
            self.record.levelProcess = process
            return _('The Level Process was successfully initialized.')

        elif 'REMOVE_SUBMIT' in self.request:
            manager = app.getSchoolToolApplication()['groups']['manager']
            process = self.record.levelProcess
            items = interfaces.IManagerWorkItems(manager).items
            # Create a copy by converting items to a tuple
            for item in tuple(items):
                if item.participant.activity.process == process:
                    items.remove(item)
            self.record.levelProcess = None
            return _('The Level Process was successfully removed.')

        elif 'WORKITEM_SUBMIT' in self.request:
            manager = app.getSchoolToolApplication()['groups']['manager']
            for item in interfaces.IManagerWorkItems(manager).items:
                if item.__name__ in self.request['workitemId']:
                    view = zapi.getMultiAdapter((item, self.request),
                                                promotion.IFinishSchemaWorkitem)
                    return view.finish()


    def history(self):
        """Return a PT-friendly history, with each entry being an info dict."""
        formatter = self.request.locale.dates.getFormatter('dateTime', 'medium')
        for record in self.record.history:
            yield {'title': record.title,
                   'description': record.description,
                   'user': record.user,
                   'timestamp': formatter.format(record.timestamp)}


    def workitems(self):
        """Get workitems for this student"""
        manager = app.getSchoolToolApplication()['groups']['manager']
        return [
            zapi.getMultiAdapter(
                (item, self.request), promotion.IFinishSchemaWorkitem)
            for item in interfaces.IManagerWorkItems(manager).items
            if (item.participant.activity.process.workflowRelevantData.student
                == self.context)]
        
