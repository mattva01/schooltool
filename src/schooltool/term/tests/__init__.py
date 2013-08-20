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
"""Testing utilities for testing Term related code.
"""
import datetime
from persistent import Persistent

from zope.location.location import LocationProxy
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.interface import implementer
from zope.interface import implements
from zope.component import adapter
from zope.component import getUtility
from zope.component import provideUtility

from z3c.form import form, field

from schooltool.utility.utility import UtilitySetUp
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.term.term import getNextTermForDate
from schooltool.term.interfaces import IDateManager
from schooltool.common import SchoolToolMessage as _


class DateManagerStub(object):
    implements(IDateManager)

    def __init__(self, today, current_term):
        self.today = today
        self.current_term = current_term


def setUpDateManagerStub(today=None, current_term=None):
    if not today:
        today = datetime.date(2005, 9, 20)
    provideUtility(DateManagerStub(today, current_term))


class LocalDateManagerUtility(Persistent, DateManagerStub):
    implements(IDateManager)

    def __init__(self):
        self.today = datetime.date(2005, 2, 1)

    @property
    def current_term(self):
        return getNextTermForDate(self.today)


dateManagerSetupSubscriber = UtilitySetUp(
    LocalDateManagerUtility, IDateManager)


@implementer(IDateManager)
@adapter(ISchoolToolApplication)
def getDateManager(context):
    return LocationProxy(getUtility(IDateManager), context, 'time')


class DateManagementView(form.EditForm):
    label = _("Set the date for the school")
    template = ViewPageTemplateFile('date_management.pt')

    form.extends(form.EditForm)
    fields = field.Fields(IDateManager)

    def updateActions(self):
        super(DateManagementView, self).updateActions()
        self.actions['apply'].addClass('button-ok')
