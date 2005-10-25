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
Student Promotion Process Implementation

$Id$
"""

import time
import persistent

import zope.interface
import zope.schema
import zope.wfmc
from zope.app import location
from zope.app.annotation.interfaces import IAnnotations

from schooltool import SchoolToolMessage as _
from schooltool import group
from schooltool.app import app
from schooltool.level import interfaces, record


WorkItemsKey = 'schooltool.workflows.promotion.workitems'

class ManagerWorkItems(persistent.dict.PersistentDict):
    zope.interface.implements(interfaces.IManagerWorkItems)

    counter = 0

    def __init__(self, context):
        super(ManagerWorkItems, self).__init__()
        self.context = context

    def addWorkItem(self, item):
        """Add a work item to the manager group."""
        id = str(self.counter)
        self.counter += 1
        location.location.locate(item, self.context, id)
        self[id] = item

    def removeWorkItem(self, item):
        del self[item.__name__]


def getManagerWorkItems(manager):
    annotations = IAnnotations(manager)
    return annotations.setdefault(WorkItemsKey, ManagerWorkItems(manager))

class Manager(persistent.Persistent):
    zope.component.adapts(zope.wfmc.interfaces.IActivity)
    zope.interface.implements(zope.wfmc.interfaces.IParticipant)

    def __init__(self, activity):
        self.activity = activity
        manager = app.getSchoolToolApplication()['groups']['manager']
        self.workItems = interfaces.IManagerWorkItems(manager)


class ProgressToNextLevel(object):
    """Progress the student to the next level.

    Type: Automatic; no user interaction required.
    """
    zope.component.adapts(zope.wfmc.interfaces.IParticipant)
    zope.interface.implements(zope.wfmc.interfaces.IWorkItem)

    def __init__(self, participant):
        self.participant = participant

    def start(self, level):
        self.finish(level.nextLevel)

    def finish(self, level):
        self.participant.activity.workItemFinished(self, level)


class ISelectInitialLevelSchema(zope.interface.Interface):
    """Select Initial Level"""

    level = zope.schema.Choice(
        title=_("Level"),
        description=_("The initial level of the student in the school."),
        vocabulary="Levels",
        required=True)


class SelectInitialLevel(persistent.Persistent, location.location.Location):
    """Select the inital level of the student.

    Type: Manual; the manager must select the initial level.
    """
    zope.component.adapts(zope.wfmc.interfaces.IParticipant)
    zope.interface.implements(zope.wfmc.interfaces.IWorkItem)

    schema = ISelectInitialLevelSchema

    def __init__(self, participant):
        self.participant = participant
        self.participant.workItems.addWorkItem(self)

    def start(self):
        pass

    def finish(self, level):
        self.participant.workItems.removeWorkItem(self)
        self.participant.activity.workItemFinished(self, level)


class ISetLevelOutcomeSchema(zope.interface.Interface):
    """Set Level Outcome"""

    outcome = zope.schema.Choice(
        title=_("Outcome"),
        description=_("Outcome of the level."),
        values=[_('pass'), _('fail'), _('withdraw')],
        required=True,
        default=_('pass'))


class SetLevelOutcome(persistent.Persistent, location.location.Location):
    """Set the level outcome of the current level.

    The student can either: 'pass', 'fail', 'withdraw'

    Type: Manual; the manager must select the initial level.
    """
    zope.component.adapts(zope.wfmc.interfaces.IParticipant)
    zope.interface.implements(zope.wfmc.interfaces.IWorkItem)

    schema = ISetLevelOutcomeSchema

    def __init__(self, participant):
        self.participant = participant
        self.participant.workItems.addWorkItem(self)

    def start(self):
        pass

    def finish(self, outcome):
        self.participant.workItems.removeWorkItem(self)
        self.participant.activity.workItemFinished(self, outcome)


class UpdateStatus(object):
    """Update the student's status.

    The student's status is being updated depending on the activity.

    Type: Automatic; no user interaction required.
    """
    zope.component.adapts(zope.wfmc.interfaces.IParticipant)
    zope.interface.implements(zope.wfmc.interfaces.IWorkItem)

    def __init__(self, participant):
        self.participant = participant

    def start(self, student):
        rec = interfaces.IAcademicRecord(student)
        act_id = self.participant.activity.definition.id
        if act_id == 'enroll':
            rec.status = 'Enrolled'

        elif act_id == 'graduate':
            rec.status = 'Graduated'

        elif act_id == 'withdraw':
            rec.status = 'Withdrawn'

        self.finish()

    def finish(self):
        self.participant.activity.workItemFinished(self)


class WriteRecord(object):
    """Make a record entry into the student's academic history.

    The record added depends on the current activity.

    Type: Automatic; no user interaction required.
    """
    zope.component.adapts(zope.wfmc.interfaces.IParticipant)
    zope.interface.implements(zope.wfmc.interfaces.IWorkItem)

    def __init__(self, participant):
        self.participant = participant

    def start(self, student, level):
        rec = interfaces.IAcademicRecord(student)
        act_id = self.participant.activity.definition.id
        if act_id == 'enroll':
            rec.history.addRecord(record.HistoricalRecord(
                u'Enrolled', u'Enrolled at school'))

        elif act_id == 'pass':
            rec.history.addRecord(record.HistoricalRecord(
                u'Passed', u'Passed level "%s"' %level.title))

        elif act_id == 'fail':
            rec.history.addRecord(record.HistoricalRecord(
                u'Failed', u'Failed level "%s"' %level.title))

        elif act_id == 'withdraw':
            rec.history.addRecord(record.HistoricalRecord(
                u'Withdrawn',
                u'Withdrew before or during level "%s"' %level.title))

        self.finish()

    def finish(self):
        self.participant.activity.workItemFinished(self)


def addProcessToStudent(event):
    if event.process.process_definition_identifier == 'schooltool.promotion':
        student = event.process.workflowRelevantData.student
        interfaces.IAcademicRecord(student).levelProcess = event.process


def removeProcessFromStudent(event):
    if event.process.process_definition_identifier == 'schooltool.promotion':
        student = event.process.workflowRelevantData.student
        interfaces.IAcademicRecord(student).levelProcess = None
