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
Academic Record Implementation

$Id$
"""
import datetime
import persistent
import zope.component
import zope.interface
import zope.security
from zope.app.annotation.interfaces import IAnnotations

from schooltool import person
from schooltool.level import interfaces


AcademicRecordKey = "schooltool.AcademicRecord"


class History(persistent.list.PersistentList):
    """Academic History of a Student"""

    __parent__ = None

    def addRecord(self, record):
        record.__parent__ = self
        self.append(record)


class HistoricalRecord(persistent.Persistent):
    """A simple historical record."""
    zope.interface.implements(interfaces.IHistoricalRecord)

    __parent__ = None

    def __init__(self, title, description=u''):
        self.timestamp = datetime.datetime.now()
        inter = zope.security.management.getInteraction()
        if inter.participations:
            self.user = inter.participations[0].principal.id
        else:
            self.user = '<unknown>'
        self.title = title
        self.description = description

    def __repr__(self):
        return "HistoricalRecord('%s' at %s)" %(
            self.title, self.timestamp.strftime('%Y/%m/%d %H:%M'))


class RecordProperty(object):
    """A property of the academic record."""

    def __init__(self, name, default=None):
        self.__name = name
        self.__default = None

    def __get__(self, inst, class_):
        return inst.record.get(self.__name, self.__default)

    def __set__(self, inst, value):
        inst.record[self.__name] = value


class AcademicRecord(object):
    zope.component.adapts(person.interfaces.IPerson)
    zope.interface.implements(interfaces.IAcademicRecord)

    history = RecordProperty('history')
    status = RecordProperty('status')
    levelProcess = RecordProperty('levelProcess')

    def __init__(self, student):
        annotations = IAnnotations(student)
        self.context = student
        self.record = annotations.get(AcademicRecordKey)

        # Initialize the record, since it does not exist yet.
        if self.record is None:
            annotations[AcademicRecordKey] = persistent.dict.PersistentDict()
            self.record = annotations.get(AcademicRecordKey)
            self.history = History()
            self.history.__parent__ = self.context
            self.status = None
            self.levelProcess = None
        
