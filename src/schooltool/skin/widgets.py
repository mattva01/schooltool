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
"""
Widgets.
"""
import zope.schema
import zope.app.form
from zope.traversing.browser.absoluteurl import absoluteURL
from zope.schema.interfaces import IField, IDate
from zope.schema.fieldproperty import FieldProperty
from zope.component import adapts, adapter
from zope.interface import implements, implementsOnly, implementer
from zope.interface import Interface
from zope.html.field import IHtmlFragmentField
from zope.publisher.interfaces.browser import IBrowserRequest
import zope.html.widget

import zc.resourcelibrary
from zc.datetimewidget.datetimewidget import DateWidget

import z3c.form
import z3c.form.interfaces
from z3c.form.widget import Widget, FieldWidget, ComputedWidgetAttribute
from z3c.form.converter import BaseDataConverter
from z3c.form.converter import FormatterValidationError
from z3c.form.browser.text import TextWidget
from z3c.form.browser.textarea import TextAreaWidget

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
        try:
            return value.strftime("%Y-%m-%d")
        except (ValueError,):
            # XXX: may be evil, but this allows users to fix incorrect
            #      dates entered before we added the >= 1900 check
            return str(value)

    def toFieldValue(self, value):
        """See interfaces.IDataConverter"""
        if value == u'':
            return self.field.missing_value
        try:
            value = parse_date(value)
        except (ValueError,):
            raise FormatterValidationError(
                _("The datetime string did not match the pattern yyyy-mm-dd"),
                value)
        try:
            value.strftime("%Y-%m-%d")
        except (ValueError,):
            raise FormatterValidationError(
                _('Year has to be equal or greater than 1900'),
                value)
        return value


class IFCKConfig(Interface):

    width = zope.schema.Int(
        title=u"Width",
        description=u"Editor frame width")

    height = zope.schema.Int(
        title=u"Height",
        description=u"Editor frame height")

    toolbar = zope.schema.TextLine(
        title=u"Toolbar configuration",
        description=u"The name of the toolbar configuration to use.")

    path = zope.schema.TextLine(
        title=u"Relative configuration path",
        description=u"Path to the FCKconfiguration javascript file.")


class FCKConfig(object):
    """Configuration of the FCK editor widget."""
    implements(IFCKConfig)

    toolbar = u"schooltool"
    path = u"/@@/editor_config.js"

    def __init__(self, width=430, height=300):
        self.width = width
        self.height = height

    def __repr__(self):
        return '<%s.%s (%d x %d, %r toolbar, %r)>' % (
            self.__class__.__module__,
            self.__class__.__name__,
            self.width, self.height,
            self.toolbar, self.path)


class IFckeditorWidget(z3c.form.interfaces.IWidget):

    config = zope.schema.Object(
        title=u"Configuration",
        description=u"CKeditor configuration.",
        schema=IFCKConfig)


class FckeditorWidgetBase(object):

    config = None # IFCKConfig

    @property
    def editor_var_name(self):
        return 'CKeditor_%s' % str(hash(self.name)).replace('-', 'u')

    @property
    def element_id(self):
        return self.id

    @property
    def script(self):
        zc.resourcelibrary.need("ckeditor")
        config = self.config

        app_url = absoluteURL(ISchoolToolApplication(None), self.request)
        fck_config_path = '%s%s' % (
            app_url, config.path)

        # XXX: using some values that may be not JS safe
        return '''
            <script type="text/javascript" language="JavaScript">
                var %(variable)s = new CKEDITOR.replace("%(id)s",
                    {
                        height: %(height)s,
                        width: %(width)s,
                        customConfig: "%(customConfigPath)s",
                    }
                );
            </script>
            ''' % {
            'id': self.element_id,
            'variable': self.editor_var_name,
            'width': config.width,
            'height': config.height,
            'toolbar': config.toolbar,
            'customConfigPath': fck_config_path,
            }


class FckeditorFormlibWidget(zope.app.form.browser.TextAreaWidget,
                             FckeditorWidgetBase):

    def __init__(self, *args, **kw):
        zope.app.form.browser.TextAreaWidget.__init__(self, *args, **kw)
        self.config = FCKConfig()

    @property
    def editor_var_name(self):
        return 'CKeditor_%s' % self.name.split('.', 1)[-1]

    @property
    def element_id(self):
        return self.name

    def __call__(self):
        zc.resourcelibrary.need("ckeditor")
        textarea = zope.app.form.browser.TextAreaWidget.__call__(self)
        script = self.script
        return '%s\n%s' % (textarea, script)


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


class FckeditorZ3CFormWidget(TextAreaWidget,
                             HTMLFragmentWidget,
                             FckeditorWidgetBase):
    """FCK editor z3c.form widget implementation."""
    implementsOnly(IFckeditorWidget)

    config = None
    value = u''

    _adapterValueAttributes = Widget._adapterValueAttributes + ('config', )


@adapter(IField, z3c.form.interfaces.IFormLayer)
@implementer(z3c.form.interfaces.IFieldWidget)
def FckeditorFieldWidget(field, request):
    """Editor widget bound to a field."""
    return FieldWidget(field, FckeditorZ3CFormWidget(request))


# The default configuration for FckeditorZ3CFormWidget
Fckeditor_config = ComputedWidgetAttribute(
    lambda a: FCKConfig(),
    request=IBrowserRequest,
    widget=IFckeditorWidget,
    )


# XXX: EditFormFCKConfig will now be applied to all add and edit forms.
#      This is wrong, but we do not have standard SchoolTool add/edit
#      z3c.forms yet, like we do with formlib; as a result, we do not have
#      standard interfaces (for example ISchooltoolAddForm) that we could
#      hook the config on.
Fckeditor_addform_config = ComputedWidgetAttribute(
    lambda a: FCKConfig(306, 200),
    context=None,
    request=IBrowserRequest,
    view=z3c.form.interfaces.IAddForm,
    field=IHtmlFragmentField,
    widget=IFckeditorWidget,
    )

Fckeditor_editform_config = ComputedWidgetAttribute(
    lambda a: FCKConfig(306, 200),
    context=None,
    request=IBrowserRequest,
    view=z3c.form.interfaces.IEditForm,
    field=IHtmlFragmentField,
    widget=IFckeditorWidget,
    )

