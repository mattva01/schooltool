#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2009 Shuttleworth Foundation
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
Inline page templates
"""

from zope.app.pagetemplate.engine import TrustedAppPT
from zope.pagetemplate.pagetemplate import PageTemplate


class InlinePageTemplate(TrustedAppPT, PageTemplate):
    """Inline page template.

    Use it like this:

        >>> pt = InlinePageTemplate('''
        ... <p tal:repeat="item items" tal:content="item">(item)</p>
        ... ''')
        >>> print pt(items=['a', 'b', 'c']).strip()
        <p>a</p>
        <p>b</p>
        <p>c</p>

    """

    def __init__(self, source, content_type=None):
        self.source = source
        if content_type is not None:
            self.content_type = content_type
        self.pt_edit(source, self.content_type)

    def pt_getContext(self, args, options):
        namespace = {'template': self, 'args': args, 'nothing': None}
        namespace.update(self.pt_getEngine().getBaseNames())
        namespace.update(options)
        return namespace
