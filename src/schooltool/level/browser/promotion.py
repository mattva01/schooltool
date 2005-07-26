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
Promotion Workflow Views

$Id: app.py 3481 2005-04-21 15:28:29Z bskahan $
"""
import zope.interface
import zope.schema
from zope.app import zapi
from zope.app.publisher import browser
from zope.app import form

from schooltool import app
from schooltool import SchoolToolMessageID as _
from schooltool.level import interfaces, promotion


class IFinishSchemaWorkitem(zope.interface.Interface):
    """A view that can finish a workflow item by getting the needed data from
       the request."""


class SchemaWorkItemView(browser.BrowserView):
    """Set the initial level of the student."""

    def __init__(self, workitem, request):
        super(SchemaWorkItemView, self).__init__(workitem, request)
        form.utility.setUpEditWidgets(self, workitem.schema,
                                      prefix=workitem.__name__)

    def widgets(self):
        return [
            getattr(self, name+'_widget')
            for name in zope.schema.getFieldNamesInOrder(self.context.schema)]

    def finish(self):
        """Complete the workitem."""
        kwargs = form.utility.getWidgetsData(self, self.context.schema)
        self.context.finish(**kwargs)
        return _('Work Item successfully finished.')


class PromotionWorkItemsView(browser.BrowserView):
    """Managament view for promoting students efficiently."""

    def students(self):
        """Return PT-friendly list of student infos"""
        return [
            {'name': id, 'title': person.title, 'username': person.username}
            for id, person in app.getSchoolToolApplication()['persons'].items()
            if interfaces.IAcademicRecord(person).levelProcess == None]
    
    def initialLevelItems(self):
        """Return PT-friendly list of students who need to be initialized"""
        manager = app.getSchoolToolApplication()['groups']['manager']
        for item in interfaces.IManagerWorkItems(manager).items:
            if zapi.isinstance(item, promotion.SelectInitialLevel):
                wfData = item.participant.activity.process.workflowRelevantData
                yield {'id': item.__name__,
                       'student': wfData.student,
                       'item_view': SchemaWorkItemView(item, self.request)}

    def outcomeItems(self):
        """Return PT-friendly list of students who need to be promoted"""
        manager = app.getSchoolToolApplication()['groups']['manager']
        for item in interfaces.IManagerWorkItems(manager).items:
            if zapi.isinstance(item, promotion.SetLevelOutcome):
                wfData = item.participant.activity.process.workflowRelevantData
                yield {'id': item.__name__,
                       'level': wfData.level,
                       'student': wfData.student,
                       'item_view': SchemaWorkItemView(item, self.request)}
                
    def update(self):
        """Update the workflows."""
        if 'ENROLL_SUBMIT' in self.request:
            persons = app.getSchoolToolApplication()['persons']
            pd = zapi.getUtility(zope.wfmc.interfaces.IProcessDefinition,
                                 name='schooltool.promotion')

            if 'ids' not in self.request:
                return _('No students were selected.')
            
            for id in self.request['ids']:
                student = persons[id]
                process = pd()
                process.start(student, None, None)

            return _('Students successfully enrolled.')


        elif 'WORKFLOW_SUBMIT' in self.request:
            manager = app.getSchoolToolApplication()['groups']['manager']

            if 'ids' not in self.request:
                return _('No students were selected.')

            ids = self.request['ids']
            # Make a copy of the list by making it a tuple
            for item in tuple(interfaces.IManagerWorkItems(manager).items):
                if item.__name__ in ids:
                    view = SchemaWorkItemView(item, self.request)
                    view.finish()
            return _('Student processes successfully updated.')
