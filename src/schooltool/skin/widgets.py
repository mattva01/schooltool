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
Widgets.
"""
import zope.schema
from zope.traversing.browser.absoluteurl import absoluteURL
from zope.schema.interfaces import IField, IDate
from zope.schema.fieldproperty import FieldProperty
from zope.component import adapts, adapter
from zope.interface import implements, implementsOnly, implementer
from zope.interface import Interface
from zope.html.field import IHtmlFragmentField

import zc.resourcelibrary
from zc.datetimewidget.datetimewidget import DateWidget

import z3c.form.interfaces
from z3c import form
from z3c.form.widget import Widget, FieldWidget, ComputedWidgetAttribute
from z3c.form.converter import BaseDataConverter
from z3c.form.converter import FormatterValidationError
from z3c.form.browser.text import TextWidget
from z3c.form.widget import FieldWidget

from schooltool.skin.skin import ISchoolToolLayer
from schooltool.common import parse_date
from schooltool.common import SchoolToolMessage as _
from schooltool.app.interfaces import ISchoolToolApplication


class IDateTextWidget(Interface):
    pass


class CustomDateTextWidget(TextWidget, DateWidget):
    implements(IDateTextWidget)

    def date_selector_button(self):
        real_name = self.name
        self.name = self.id
        result = self._render("")
        self.name = real_name
        return result


def CustomDateFieldTextWidget(field, request):
    """IFieldWidget factory for MyWidget."""
    return FieldWidget(field, CustomDateTextWidget(request))


class CustomDateDataConverter(BaseDataConverter):
    """A special data converter for iso dates."""

    adapts(IDate, CustomDateTextWidget)

    def toWidgetValue(self, value):
        """See interfaces.IDataConverter"""
        if value is self.field.missing_value:
            return u''
        return value.strftime("%Y-%m-%d")

    def toFieldValue(self, value):
        """See interfaces.IDataConverter"""
        if value == u'':
            return self.field.missing_value
        try:
            return parse_date(value)
        except ValueError, err:
            raise FormatterValidationError(_("The datetime string did not match the pattern yyyy-mm-dd"),
                                           value)


class IHTMLFragmentWidget(zope.interface.Interface):
    """The HTML element 'core' attributes."""

    id = zope.schema.BytesLine(
        title=u'Id',
        description=(u'This attribute assigns a name to an element. This '
                     u'name must be unique in a document.'),
        required=False)


class HTMLFragmentWidget(object):
    implements(IHTMLFragmentWidget)

    id = FieldProperty(IHTMLFragmentWidget['id'])


class IFCKConfig(Interface):

    width = zope.schema.Int(
        title=_(u"Width"),
        description=_(u"Editor frame width"))

    height = zope.schema.Int(
        title=_(u"Height"),
        description=_(u"Editor frame height"))

    toolbar = zope.schema.TextLine(
        title=_(u"Toolbar configuration"),
        description=_(u"The name of the toolbar configuration to use."))

    path = zope.schema.TextLine(
        title=_(u"Configuration path"),
        description=_(u"Path to the FCKconfiguration javascript file."))



class IFckeditorWidget(form.interfaces.IWidget):

    config = zope.schema.Object(
        title=_(u"Configuration"),
        description=_(u"FCK editor configuration."),
        schema=IFCKConfig)


class FckeditorWidget(Widget, HTMLFragmentWidget):
    """FCK editor widget implementation."""
    implementsOnly(IFckeditorWidget)

    config = None
    value = u''

    _adapterValueAttributes = Widget._adapterValueAttributes + ('config', )

    @property
    def script(self):
        zc.resourcelibrary.need("fckeditor")
        config = IFCKConfig(self.config)
        # XXX: using some values that may be not JS safe
        return '''
            <script type="text/javascript" language="JavaScript">
                var %(variable)s = new FCKeditor(
                    "%(id)s",
                     %(width)d,
                     %(height)d,
                     "%(toolbar)s");
                %(variable)s.BasePath = "/@@/fckeditor/";
                %(variable)s.Config["CustomConfigurationsPath"] = "%(configPath)s";
                %(variable)s.ReplaceTextarea();
            </script>
            ''' % {
            'id': self.id,
            'variable': 'oFCKeditor_%s' % str(hash(self.name)).replace('-', 'u'),
            'width': config.width,
            'height': config.height,
            'toolbar': config.toolbar,
            'configPath': config.path,
            }


@adapter(IField, form.interfaces.IFormLayer)
@implementer(form.interfaces.IFieldWidget)
def FckeditorFieldWidget(field, request):
    """Editor widget bound to a field."""
    return FieldWidget(field, FckeditorWidget(request))


class FCKConfig(object):
    """Configuration of the FCK editor widget."""
    implements(IFCKConfig)

    width = 430
    height = 300
    toolbar = u"schooltool"
    path = u""

    def __init__(self, adapter):
        # adapter is expected to have following attributes:
        # context, request, view, field, widget
        self.adapter = adapter
        url = absoluteURL(ISchoolToolApplication(None),
                          self.adapter.request)
        self.path = (url + '/@@/editor_config.js')


# The default configuration for FckeditorWidget
Fckeditor_config = ComputedWidgetAttribute(
    FCKConfig,
    request=ISchoolToolLayer,
    widget=IFckeditorWidget,
    )


class EditFormFCKConfig(FCKConfig):
    width = 306
    height = 200


# XXX: EditFormFCKConfig will now be applied to all add and edit forms.
#      This is wrong, but we do not have standard SchoolTool add/edit
#      z3c.forms yet, like we do with formlib; as a result, we do not have
#      standard interfaces (for example ISchooltoolAddForm) that we could
#      hook the config on.
Fckeditor_addform_config = ComputedWidgetAttribute(
    EditFormFCKConfig,
    context=None,
    request=ISchoolToolLayer,
    view=form.interfaces.IAddForm,
    field=IHtmlFragmentField,
    widget=IFckeditorWidget,
    )

Fckeditor_editform_config = ComputedWidgetAttribute(
    EditFormFCKConfig,
    context=None,
    request=ISchoolToolLayer,
    view=form.interfaces.IEditForm,
    field=IHtmlFragmentField,
    widget=IFckeditorWidget,
    )
