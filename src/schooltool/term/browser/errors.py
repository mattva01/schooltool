#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2008 Shuttleworth Foundation
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
Term error views.
"""
from zope.component import adapts
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile

from z3c.form.error import ErrorViewSnippet

from schooltool.schoolyear.interfaces import TermOverlapError


class OverlapErrorViewSnippet(ErrorViewSnippet):
    adapts(TermOverlapError, None, None, None, None, None)

    render = ViewPageTemplateFile("templates/term_overlap_error.pt")

    def terms(self):
        return self.context.overlapping_terms

    def createMessage(self):
        return self.context.__repr__()
