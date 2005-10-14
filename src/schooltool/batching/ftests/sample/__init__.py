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
Browser view for sample batch implementation

$Id: browser.py 4857 2005-08-24 20:51:55Z srichter $
"""
from zope.interface import implements
from zope.publisher.interfaces.browser import IBrowserPublisher
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.app.publisher.browser import BrowserView

from schooltool.batching import Batch

class BatchView(BrowserView):
    """A sample view that implements batching."""
    implements(IBrowserPublisher)

    data = ['Item%03d' % i for i in range(1000)]

    index = ViewPageTemplateFile('view.pt')

    def __call__(self):
        start = int(self.request.get('batch_start', 0))
        size = int(self.request.get('batch_size', 10))
        self.batch = Batch(self.data, start, size)
        return self.index()

