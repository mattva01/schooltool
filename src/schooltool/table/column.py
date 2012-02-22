#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2012 Shuttleworth Foundation
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
More columns for tables.
"""
import datetime

from zope.interface import implements
from zope.i18n.interfaces.locales import ICollator
from zope.i18n import translate
from zope.component import queryAdapter, queryMultiAdapter
from zope.security.proxy import removeSecurityProxy
from zope.app.dependable.interfaces import IDependable
from zope.traversing.browser.absoluteurl import absoluteURL

from zc.table import column
from zc.table.interfaces import ISortableColumn
from zc.table.column import GetterColumn

from schooltool.common import stupid_form_key
from schooltool.table.interfaces import ICheckboxColumn


#XXX: Misplaced helper
def getResourceURL(library_name, image_name, request):
    if not image_name:
        return None
    if library_name is not None:
        library = queryAdapter(request, name=library_name)
        image = library.get(image_name)
    else:
        image = queryAdapter(request, name=image_name)
    if image is None:
        return None
    return absoluteURL(image, request)


class CheckboxColumn(column.Column):
    """A columns with a checkbox

    The name and id of the checkbox are composed of the prefix keyword
    argument and __name__ (or other value if form_id_builder is specified) of
    the item being displayed.
    """
    implements(ICheckboxColumn)

    def __init__(self, prefix, name=None, title=None,
                 isDisabled=None, id_getter=None):
        super(CheckboxColumn, self).__init__(name=name, title=title)
        if isDisabled:
            self.isDisabled = isDisabled
        self.prefix = prefix
        if id_getter is None:
            self.id_getter = stupid_form_key
        else:
            self.id_getter = id_getter

    def isDisabled(self, item):
        return False

    def renderCell(self, item, formatter):
        if not self.isDisabled(item):
            form_id = ".".join(filter(None, [self.prefix, self.id_getter(item)]))
            return '<input type="checkbox" name="%s" id="%s" />' % (
                form_id, form_id)
        else:
            return ''


class DependableCheckboxColumn(CheckboxColumn):
    """A column that displays a checkbox that is disabled if item has dependables.

    The name and id of the checkbox are composed of the prefix keyword
    argument and __name__ of the item being displayed.
    """

    def __init__(self, *args, **kw):
        kw = dict(kw)
        self.show_disabled = kw.pop('show_disabled', True)
        super(DependableCheckboxColumn, self).__init__(*args, **kw)

    def renderCell(self, item, formatter):
        form_id = ".".join(filter(None, [self.prefix, self.id_getter(item)]))
        if self.hasDependents(item):
            if self.show_disabled:
                return '<input type="checkbox" name="%s" id="%s" disabled="disabled" />' % (form_id, form_id)
            else:
                return ''
        else:
            checked = form_id in formatter.request and 'checked="checked"' or ''
            return '<input type="checkbox" name="%s" id="%s" %s/>' % (
                form_id, form_id, checked)

    def hasDependents(self, item):
        # We cannot adapt security-proxied objects to IDependable.  Unwrapping
        # is safe since we do not modify anything, and the information whether
        # an object can be deleted or not is not classified.
        unwrapped_context = removeSecurityProxy(item)
        dependable = IDependable(unwrapped_context, None)
        if dependable is None:
            return False
        else:
            return bool(dependable.dependents())


class DateColumn(column.GetterColumn):
    """Table column that displays dates.

    Sortable even when None values are around.
    """

    def getSortKey(self, item, formatter):
        if self.getter(item, formatter) is None:
            return datetime.date.min
        else:
            return self.getter(item, formatter)

    def cell_formatter(self, maybe_date, item, formatter):
        view = queryMultiAdapter((maybe_date, formatter.request),
                                 name='mediumDate',
                                 default=lambda: '')
        return view()


class LocaleAwareGetterColumn(GetterColumn):
    """Getter columnt that has locale aware sorting."""

    implements(ISortableColumn)

    def getSortKey(self, item, formatter):
        collator = ICollator(formatter.request.locale)
        s = self.getter(item, formatter)
        return s and collator.key(s)


class ImageInputColumn(column.Column):

    def __init__(self, prefix, title=None, name=None,
                 alt=None, library=None, image=None, id_getter=None):
        super(ImageInputColumn, self).__init__(title=title, name=name)
        self.prefix = prefix
        self.alt = alt
        self.library = library
        self.image = image
        if id_getter is None:
            self.id_getter = stupid_form_key
        else:
            self.id_getter = id_getter

    def params(self, item, formatter):
        image_url = getResourceURL(self.library, self.image, formatter.request)
        if not image_url:
            return None
        form_id = ".".join(filter(None, [self.prefix, self.id_getter(item)]))
        return {
            'title': translate(self.title, context=formatter.request) or '',
            'alt': translate(self.alt, context=formatter.request) or '',
            'name': form_id,
            'src': image_url,
            }

    def renderCell(self, item, formatter):
        params = self.params(item, formatter)
        if not params:
            return ''
        return self.template() % params

    def template(self):
        return '\n'.join([
                '<button class="image" type="submit" name="%(name)s" title="%(title)s" value="1">',
                '<img src="%(src)s" alt="%(alt)s" />',
                '</button>'
                ])


class ImageInputValueColumn(ImageInputColumn):

    on_click = ""

    def __init__(self, *args, **kw):
        on_click = kw.pop('on_click', "")
        ImageInputColumn.__init__(self, *args, **kw)
        self.on_click = on_click
        self.form_id = ".".join(filter(None, [self.prefix, self.name]))

    def params(self, item, formatter):
        image_url = getResourceURL(self.library, self.image, formatter.request)
        if not image_url:
            return None
        value = self.id_getter(item)
        return {
            'title': translate(self.title, context=formatter.request) or '',
            'alt': translate(self.alt, context=formatter.request) or '',
            'name': self.form_id,
            'value': value,
            'src': image_url,
            'on_click': self.on_click,
            }

    def template(self):
        return '\n'.join([
                '<button class="image" type="submit" name="%(name)s"'
                ' title="%(title)s" value="%(value)s" onclick="%(on_click)s">',
                '<img src="%(src)s" alt="%(alt)s" />',
                '</button>'
                ])
