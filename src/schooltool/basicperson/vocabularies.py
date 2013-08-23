#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2007 Shuttleworth Foundation
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
Sources and vocabularies for form fields.
"""
from zope.interface import implements
from zope.interface import implementer
from zope.component import adapter

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.utils import vocabulary
from schooltool.person.interfaces import IPerson
from schooltool.group.interfaces import IGroupContainer
from schooltool.group.interfaces import IGroup

from schooltool.basicperson.browser.person import PersonTerm
from schooltool.basicperson.browser.person import GroupTerm
from schooltool.basicperson.interfaces import IGroupVocabulary
from schooltool.basicperson.interfaces import IBasicPersonVocabulary
from schooltool.basicperson.interfaces import IDemographicsFields
from schooltool.basicperson.interfaces import IFieldDescription
from schooltool.basicperson.interfaces import IFieldFilterVocabulary

from schooltool.common import SchoolToolMessage as _


class GroupVocabulary(object):
    implements(IGroupVocabulary)

    def __init__(self, context):
        self.context = context

    def __len__(self):
        return len(self.context.groups)

    def __contains__(self, value):
        return True

    def __iter__(self):
        if IPerson.providedBy(self.context):
            groups = [group for group in self.context.groups
                      if IGroup.providedBy(group)]
        else:
            groups = list(IGroupContainer(ISchoolToolApplication(None), {}).values())

        for group in sorted(groups, key=lambda g: g.__name__):
            yield GroupTerm(group)

    def getTermByToken(self, token):
        gc = IGroupContainer(ISchoolToolApplication(None))
        if gc is None:
            raise LookupError(token)
        if token not in gc:
            raise LookupError(token)
        return GroupTerm(gc[token])

    def getTerm(self, value):
        return GroupTerm(value)


def groupVocabularyFactory():
    return GroupVocabulary


class AdvisorVocabulary(object):
    implements(IBasicPersonVocabulary)

    def __init__(self, context):
        self.context = context

    def __contains__(self, value):
        return True

    def __len__(self):
        return len(self.context.advisors)

    def __iter__(self):
        gc = IGroupContainer(ISchoolToolApplication(None), None)
        if gc is None:
            return
        persons = gc['teachers'].members
        for person in sorted(persons, key=lambda p: p.__name__):
            yield PersonTerm(person)

    def getTermByToken(self, token):
        app = ISchoolToolApplication(None)
        pc = app['persons']
        if token not in pc:
            raise LookupError(token)
        return PersonTerm(pc[token])

    def getTerm(self, value):
        return PersonTerm(value)


def advisorVocabularyFactory():
    return AdvisorVocabulary


def LimitKeyVocabFactory():
    return IFieldFilterVocabulary


@adapter(IFieldDescription)
@implementer(IFieldFilterVocabulary)
def getLimitKeyVocabularyForFieldDescription(field_description):
    field_container = field_description.__parent__
    return IFieldFilterVocabulary(field_container)


@adapter(IDemographicsFields)
@implementer(IFieldFilterVocabulary)
def getLimitKeyVocabularyForPersonFields(person_field_description_container):
    return vocabulary([
        ('students', _('Students')),
        ('teachers', _('Teachers')),
        ('administrators', _('Administrators')),
        ])

