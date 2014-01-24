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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
More columns for tables.
"""
import datetime

from zope.app.dependable.interfaces import IDependable
from zope.interface import implementer, implements, classImplements
from zope.i18n.interfaces.locales import ICollator
from zope.i18n import translate
from zope.intid.interfaces import IIntIds
from zope.interface import implementsOnly
from zope.component import adapter, queryMultiAdapter
from zope.component import queryUtility
from zope.security.proxy import removeSecurityProxy

import zc.table
import zc.table.interfaces
import zc.table.column

from schooltool.common import stupid_form_key, getResourceURL
from schooltool.table.interfaces import ICheckboxColumn
from schooltool.table.interfaces import IIndexedColumn


class CheckboxColumn(zc.table.column.Column):
    """A columns with a checkbox

    The name and id of the checkbox are composed of the prefix keyword
    argument and __name__ (or other value if form_id_builder is specified) of
    the item being displayed.
    """
    implements(ICheckboxColumn)

    def __init__(self, prefix, name=None, title=None,
                 isDisabled=None, id_getter=None,
                 value_getter=None):
        super(CheckboxColumn, self).__init__(name=name, title=title)
        if isDisabled:
            self.isDisabled = isDisabled
        self.prefix = prefix
        if id_getter is None:
            self.id_getter = stupid_form_key
        else:
            self.id_getter = id_getter
        self.value_getter = value_getter

    def isDisabled(self, item):
        return False

    def template(self):
        return '<input type="checkbox" name="%(name)s" id="%(id)s"%(checked)s />'

    def params(self, item, formatter):
        checked = False
        if self.value_getter is not None:
            checked = bool(self.value_getter(item))
        form_id = ".".join(filter(None, [self.prefix, self.id_getter(item)]))
        return {
            'name': form_id,
            'id': form_id,
            'checked': checked and ' checked="checked"' or '',
            }

    def renderCell(self, item, formatter):
        if not self.isDisabled(item):
            params = self.params(item, formatter)
            return self.template() % params
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


class DateColumn(zc.table.column.GetterColumn):
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


class LocaleAwareGetterColumn(zc.table.column.GetterColumn):
    """Getter columnt that has locale aware sorting."""

    implements(zc.table.interfaces.ISortableColumn)

    def getSortKey(self, item, formatter):
        collator = ICollator(formatter.request.locale)
        s = self.getter(item, formatter)
        return s and collator.key(s)


class ImageInputColumn(zc.table.column.Column):

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


class TableSubmitImageColumn(ImageInputColumn):

    def __init__(self, prefix, title=None, name=None, alt=None,
                 library='schooltool.skin.flourish', image=None,
                 container_id='', id_getter=None):
        super(TableSubmitImageColumn, self).__init__(
            prefix, title=title, name=name, alt=alt,
            library=library, image=image, id_getter=id_getter)
        self.form_id = ".".join(filter(None, [self.prefix, self.name]))
        self.container_id = container_id

    def on_click(self, formatter):
        return "return ST.table.on_form_submit('%s', this)" % self.container_id

    def params(self, item, formatter):
        image_url = getResourceURL(
            self.library, self.image, formatter.request)
        if not image_url:
            return None
        return {
            'title': translate(self.title, context=formatter.request) or '',
            'alt': translate(self.alt, context=formatter.request) or '',
            'name': self.form_id,
            'value': self.id_getter(item),
            'src': image_url,
            'script': self.on_click(formatter), # XXX: should encode this
            }

    def renderCell(self, item, formatter):
        params = self.params(item, formatter)
        if not params:
            return ''
        return self.template() % params

    def template(self):
        return ' '.join(s.strip() for s in [
                '<button class="image" type="submit" name="%(name)s"'
                '        title="%(title)s" value="%(value)s"',
                '        onclick="%(script)s">',
                '  <img src="%(src)s" alt="%(alt)s" />',
                '</button>'
                ])


class MultiStateColumn(zc.table.column.Column):

    header_column = None
    state_columns = None

    def __init__(self, states=(), header=None, state_getter=None):
        zc.table.column.Column.__init__(self)
        self.header_column = header
        self.state_columns = states
        if state_getter is None:
            state_getter = lambda item: 0
        self.getState = state_getter

    def renderHeader(self, formatter):
        return self.header_column.renderHeader(formatter)

    def renderCell(self, item, formatter):
        state = self.getState(item, formatter)
        column = self.state_columns[state]
        cell = column.renderCell(item, formatter)
        return cell


class IndexedGetterColumn(zc.table.column.GetterColumn):
    implements(IIndexedColumn, zc.table.interfaces.ISortableColumn)

    def __init__(self, **kwargs):
        self.index = kwargs.pop('index')
        super(IndexedGetterColumn, self).__init__(**kwargs)

    def _sort(self, items, formatter, start, stop, sorters, multiplier):
        if self.subsort and sorters:
            items = sorters[0](items, formatter, start, stop, sorters[1:])
        else:
            items = list(items) # don't mutate original
        getSortKey = self.getSortKey

        # Patch the SortableColum._sort to use both cmp and key for sorting.
        # This reduces usage of getSortKey drastically on large datasets.
        items.sort(
            cmp=lambda a, b: multiplier*cmp(a, b),
            key=lambda item: getSortKey(item, formatter))

        return items

    def renderCell(self, item, formatter):
        item = queryUtility(IIntIds).getObject(item['id'])
        return super(IndexedGetterColumn, self).renderCell(item, formatter)

    def getSortKey(self, item, formatter):
        id = item['id']
        index = item['catalog'][self.index]
        return index.documents_to_values[id]


class IndexedLocaleAwareGetterColumn(IndexedGetterColumn):

    _cached_collator = None

    def getSortKey(self, item, formatter):
        if not self._cached_collator:
            self._cached_collator = ICollator(formatter.request.locale)
        s = super(IndexedLocaleAwareGetterColumn, self).getSortKey(item, formatter)
        return s and self._cached_collator.key(s)


def makeIndexedColumn(mixins, column, *args, **kw):
    class_ = column.__class__
    new_class = type(
        '_indexed_%s' % class_.__name__,
        tuple(mixins) + (class_,),
        {'_non_indexed_column': column})
    classImplements(new_class, IIndexedColumn)
    new_column = super(class_, new_class).__new__(new_class, *args, **kw)
    new_column.__dict__.update(dict(column.__dict__))
    return new_column


def unindex(indexed_item):
    return queryUtility(IIntIds).getObject(indexed_item['id'])


class RenderUnindexingMixin(object):
    def renderCell(self, indexed_item, formatter):
        return super(RenderUnindexingMixin, self).renderCell(
            unindex(indexed_item), formatter)


class SortUnindexingMixin(object):
    def getSortKey(self, indexed_item, formatter):
        super(SortUnindexingMixin, self).getSortKey(
            unindex(indexed_item), formatter)


@adapter(zc.table.interfaces.IColumn)
@implementer(IIndexedColumn)
def getIndexedColumn(column):
    column = makeIndexedColumn(
        [RenderUnindexingMixin], column)
    return column


@adapter(zc.table.interfaces.ISortableColumn)
@implementer(IIndexedColumn)
def getIndexedSortableColumn(column):
    column = makeIndexedColumn(
        [RenderUnindexingMixin, SortUnindexingMixin], column)
    return column


class NoSortIndexedGetterColumn(IndexedGetterColumn):
    implementsOnly(IIndexedColumn)


class NoSortIndexedLocaleAwareGetterColumn(IndexedLocaleAwareGetterColumn):
    implementsOnly(IIndexedColumn)
