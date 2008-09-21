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
Batching for schooltool.

$Id$
"""
from zope.interface import implements
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

from schooltool.table.interfaces import IBatch


class Batch(object):
    """Batching mechanism for Tables"""
    implements(IBatch)

    template = ViewPageTemplateFile("templates/batch.pt")

    def __init__(self, formatter, batch_size=25):
        self.formatter = formatter

        if formatter.prefix:
            self.name = "." + formatter.prefix
        else:
            self.name = ""

        self.request = self.formatter.request
        self.context = self.formatter

        item_list = list(self.context._items)
        self.full_size = len(item_list)
        self.extra_url = self.context.extra_url()
        self.base_url = self.request.URL

        self.start = int(self.request.get('batch_start' + self.name, 0))
        self.size = int(self.request.get('batch_size' + self.name, batch_size))
        self.length = len(item_list[self.start:self.start + self.size])

    def render(self):
        if self.size < self.full_size or self.needsBatch:
            return self.template()
        else:
            return ''

    @property
    def needsBatch(self):
        there_are_more = self.full_size > self.size + self.start
        there_were_before = self.start - self.size > 0
        return there_are_more or there_were_before

    def __len__(self):
        return self.length

    def previous_url(self):
        start = self.start - self.size
        if start >= 0:
            return '%s?batch_start%s=%s&batch_size%s=%s%s' % (
                self.base_url, self.name, start, self.name, self.size, self.extra_url)
        return None

    def next_url(self):
        start = self.size + self.start
        if self.full_size > start:
            return '%s?batch_start%s=%s&batch_size%s=%s%s' % (
                self.base_url, self.name, start, self.name, self.size, self.extra_url)

    def num(self):
        return self.start / self.size + 1

    def numBatches(self):
        num = self.full_size / self.size
        if self.full_size % self.size:
            num += 1
        return num

    def batch_urls(self):
        urls = []
        start = 0
        num = 1
        while self.full_size > start:
            css_class = None
            if (self.start == start):
                css_class = 'current'
            href = '%s?batch_start%s=%s&batch_size%s=%s%s' % (
                self.base_url, self.name, start, self.name, self.size, self.extra_url)
            urls.append({'href': href,
                         'num': num,
                         'class': css_class})
            num += 1
            start += self.size

        return urls


class IterableBatch(Batch):

    def __init__(self, items, request, extra_url=None, batch_size=25,
                 sort_by=None, name=None):
        self.context = None
        self.items = items
        self.request = request

        if name:
            self.name = "." + name
        else:
            self.name = ""

        def key(obj):
            try:
                return obj.get(sort_by)
            except AttributeError:
                return getattr(obj, sort_by)

        if sort_by is not None:
            item_list = sorted(items, key=key)
        else:
            item_list = items
        self.full_size = len(item_list)
        self.extra_url = extra_url or ""
        self.base_url = self.request.URL


        self.start = int(self.request.get('batch_start' + self.name, 0))
        self.size = int(self.request.get('batch_size' + self.name, batch_size))
        self.list = item_list[self.start:self.start + self.size]
        self.length = len(self.list)

    def __iter__(self):
        return iter(self.list)
