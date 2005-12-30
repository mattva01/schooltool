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
from zope.interface import directlyProvides
from zope.wfmc.interfaces import IProcessDefinition
from zope.component import provideAdapter, provideUtility

from schooltool.attendance.interfaces import TARDY


class WorkItemStub(object):

    def __init__(self, attendance_record):
        self.attendance_record = attendance_record

    def acceptExplanation(self):
        print "Accepted explanation"

    def rejectExplanation(self):
        print "Rejected explanation"

    def makeTardy(self, arrival_time):
        self.attendance_record.status = TARDY
        self.attendance_record.late_arrival = arrival_time


class SilentProcessDef(object):
    def start(self, arg):
        arg._work_item = WorkItemStub(arg)

directlyProvides(SilentProcessDef, IProcessDefinition)


def stubProcessDefinition():
    provideUtility(SilentProcessDef, IProcessDefinition,
                   name='schooltool.attendance.explanation')
