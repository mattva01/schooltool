#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2011 Shuttleworth Foundation
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
ZCML directives for reports

"""

from zope.configuration.fields import MessageID
from zope.interface import Interface
from zope.publisher.interfaces.browser import IBrowserView
from zope.publisher.interfaces.browser import IDefaultBrowserLayer
from zope.schema import TextLine
from zope.viewlet.metadirectives import IViewletDirective
from zope.viewlet.metaconfigure import viewletDirective

from schooltool.report.interfaces import IReportLinkViewletManager
from schooltool.report.report import ReportLinkViewlet
from schooltool.report.report import getReportRegistrationUtility


class IReportLinkDirective(IViewletDirective):
    group = MessageID(title=u"Report group", required=True)
    title = MessageID(title=u"Report link text", required=True)
    description = MessageID(title=u"Report link description", required=True)
    link = TextLine(title=u"Link to the report", required=False)


def reportLinkDirective(_context, name, permission, for_=Interface,
    layer=IDefaultBrowserLayer, view=IBrowserView,
    manager=IReportLinkViewletManager,
    class_=ReportLinkViewlet, template=None, group=u'', title=u'',
    description='', link='', **kwargs):

    # forward our defaults to the viewletDirective
    viewletDirective(_context, name, permission,
        for_=for_, layer=layer, view=view, manager=manager,
        class_=class_, template=template,
        group=group, title=title, description=description, link=link, **kwargs)

    # and register the report for reference
    utility = getReportRegistrationUtility()
    utility.registerReport(group, title, description)
