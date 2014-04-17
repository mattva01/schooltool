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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
SchoolTool flourish widgets.
"""
import time, datetime
import re
import os
import sys
from cStringIO import StringIO

try:
    import Image
except ImportError:
    from PIL import Image

import zope.formlib.widgets
import zope.datetime
from zope.component import getUtility, adapter, adapts, queryMultiAdapter
from zope.dublincore.interfaces import IZopeDublinCore
from zope.interface import implementer, Interface, implements
from zope.i18n.interfaces import INegotiator
from zope.traversing.browser.absoluteurl import absoluteURL
from zope.publisher.interfaces import NotFound
from zope.publisher.browser import BrowserPage
from zope.publisher.browser import BrowserView
from zope.schema.interfaces import IField

import z3c.form.interfaces
from z3c.form.browser.file import FileWidget
from z3c.form.widget import ComputedWidgetAttribute, FieldWidget
from z3c.form.converter import FileUploadDataConverter
from z3c.form.converter import FormatterValidationError
import zc.resourcelibrary

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.basicperson.demographics import IDemographicsForm
from schooltool.skin.widgets import CkeditorConfig
from schooltool.skin.widgets import ICkeditorWidget
from schooltool.skin.widgets import CkeditorFormlibWidget
from schooltool.skin.widgets import CkeditorZ3CFormWidget
from schooltool.skin.flourish.resource import ResourceLibrary
from schooltool.skin.flourish.interfaces import IFlourishLayer
from schooltool.skin.flourish.helpers import quoteFilename
from schooltool.common.fields import IImage, ImageFile
from schooltool.common import format_message
from schooltool.common import SchoolToolMessage as _


class JQueryI18nLibrary(ResourceLibrary):

    lib_path = None

    @classmethod
    def configure(cls):
        translation_path = cls.source
        if cls.lib_path is None:
            gdict = sys._getframe(1).f_globals
            lib_path = os.path.dirname(gdict["__file__"])
        full_path = os.path.join(lib_path, translation_path)

        locale_re = re.compile('jquery[.]ui[.]datepicker-'
                               '(?P<locale>[a-zA-Z]+([-_][a-zA-Z]+)?)'
                               '[.]js')

        cls.locales = cls.read_locale_map(full_path, locale_re)

    @classmethod
    def read_locale_map(cls, path, locale_re):
        if not os.path.isdir(path):
            raise ValueError("Not a translation directory", path)
        contents = os.listdir(path)
        locales = {}
        for name in contents:
            m = locale_re.match(name)
            if m is None:
                continue
            locale = m.groupdict()['locale']
            locales[locale] = name
        return locales

    @property
    def included(self):
        negotiator = getUtility(INegotiator)
        lang = negotiator.getLanguage(self.locales, self.request)
        if lang in self.locales:
            return (self.locales[lang], )
        return ()


class FormlibDateWidget(zope.formlib.widgets.DateWidget):
    cssClass="date-field"


Flourish_ckeditor_config = ComputedWidgetAttribute(
    lambda a: CkeditorConfig(288, 160),
    request=IFlourishLayer,
    widget=ICkeditorWidget,
    )


class FlourishCkeditorScriptBase(object):

    @property
    def script(self):
        zc.resourcelibrary.need("ckeditor")
        config = self.config

        app_url = absoluteURL(ISchoolToolApplication(None), self.request)
        config_path = '%s%s' % (
            app_url, config.path)
        skin_path = '%s/@@/schooltool.skin.flourish-ckeditor/' % (
            app_url)
        contents_css_path = '%s%s' % (skin_path, 'contents.css')

        # XXX: using some values that may be not JS safe
        return '''
            <script type="text/javascript" language="JavaScript">
                var skin = "v2,%(skinPath)s";
                if (CKEDITOR.skins == undefined) {
                    skin = "moono";
                }
                var %(variable)s = new CKEDITOR.replace("%(id)s",
                    {
                        height: %(height)s,
                        width: %(width)s,
                        customConfig: "%(customConfigPath)s",
                        skin: skin,
                        contentsCss: "%(contentsCss)s"
                    }
                );
            </script>
            ''' % {
            'id': self.element_id,
            'variable': self.editor_var_name,
            'width': config.width,
            'height': config.height,
            'customConfigPath': config_path,
            'skinPath': skin_path,
            'contentsCss': contents_css_path,
            }


class FlourishCkeditorFormlibWidget(FlourishCkeditorScriptBase,
                                    CkeditorFormlibWidget):

    def __init__(self, *args, **kw):
        super(FlourishCkeditorFormlibWidget, self).__init__(*args, **kw)
        self.config = CkeditorConfig(288, 160)


class FlourishCkeditorZ3CFormWidget(FlourishCkeditorScriptBase,
                                    CkeditorZ3CFormWidget):

    pass


@adapter(IField, IFlourishLayer)
@implementer(z3c.form.interfaces.IFieldWidget)
def FlourishCkeditorFieldWidget(field, request):
    return FieldWidget(field, FlourishCkeditorZ3CFormWidget(request))


def is_required_demo_field(adapter):
    field = adapter.field
    return field.required and field.interface is IDemographicsForm


PromptRequiredDemoField = ComputedWidgetAttribute(is_required_demo_field)


class FileDataURI(BrowserView):

    def __call__(self):
        stream = self.context.open()
        payload = stream.read().encode('base64').replace('\n','')
        stream.close()
        mime = self.context.mimeType
        return 'data:'+mime+';base64,'+payload


class IImageWidget(Interface):
    """Marker for image widgets"""


class ImageWidget(FileWidget):

    implements(IImageWidget)

    @property
    def attribute(self):
        return self.field.__name__

    @property
    def alt(self):
        return self.field.title

    def stored_value(self):
        if self.ignoreContext:
            return None
        dm = queryMultiAdapter((self.context, self.field),
                               z3c.form.interfaces.IDataManager)
        if dm is None:
            return None
        value = dm.query()
        return value


def ImageFieldWidget(field, request):
    return FieldWidget(field, ImageWidget(request))


class ImageDataConverter(FileUploadDataConverter):

    adapts(IImage, IImageWidget)

    def toFieldValue(self, value):
        if value is None or value == '':
            return z3c.form.interfaces.NOT_CHANGED
        if value == 'delete':
            # XXX: delete checkbox was marked
            return None
        data = value.read()
        try:
            image = Image.open(StringIO(data))
            if image.format not in ('JPEG', 'PNG'):
                raise IOError()
        except (IOError,):
            raise FormatterValidationError(
                _('The file uploaded is not a JPEG or PNG image'), value)
        size = len(data)
        if size > self.field.max_file_size:
            msg = _('The image uploaded cannot be larger than ${size} MB')
            raise FormatterValidationError(
                format_message(
                    msg,
                    mapping={'size': '%.2f' % (float(size) / (10**6))}),
                value)
        data = self.processImage(image)
        f = ImageFile()
        self.updateFile(f, data)
        return f

    def processImage(self, image):
        kw = {'quality': 100, 'filter': Image.ANTIALIAS}
        result = image
        if (self.field.size is not None and
            image.size != self.field.size):
            size = self.getMaxSize(image)
            image.thumbnail(size, kw['filter'])
            if image.size != self.field.size or image.mode == 'RGBA':
                result = Image.new('RGB', self.field.size, (255, 255, 255))
                left = int(round((self.field.size[0] - image.size[0])/float(2)))
                up = int(round((self.field.size[1] - image.size[1])/float(2)))
                mask = None
                if image.mode == 'RGBA':
                    mask = image
                result.paste(image, (left, up), mask)
        f = StringIO()
        result.save(f, self.field.format, **kw)
        return f.getvalue()

    def updateFile(self, ob, data):
        ob.mimeType = Image.MIME[self.field.format]
        w = ob.open("w")
        w.write(data)
        w.close()

    def getMaxSize(self, image):
        image_size = image.size
        desired_size = self.field.size
        x_ratio = float(desired_size[0])/image_size[0]
        y_ratio = float(desired_size[1])/image_size[1]
        if x_ratio < y_ratio:
            new_size = (round(x_ratio*image_size[0]),
                        round(x_ratio*image_size[1]))
        else:
            new_size = (round(y_ratio*image_size[0]),
                        round(y_ratio*image_size[1]))
        return tuple(map(int, new_size))


class ImageView(BrowserPage):

    attribute = None

    def renderImage(self, image):
        self.request.response.setHeader('Content-Type', image.mimeType)
        self.request.response.setHeader('Content-Length', image.size)
        try:
            modified = IZopeDublinCore(self.context).modified
        except TypeError:
            modified=None
        if modified is not None and isinstance(modified, datetime.datetime):
            header= self.request.getHeader('If-Modified-Since', None)
            lmt = long(time.mktime(modified.timetuple()))
            if header is not None:
                header = header.split(';')[0]
                try:
                    mod_since=long(time(header))
                except:
                    mod_since=None
                if mod_since is not None:
                    if lmt <= mod_since:
                        self.request.response.setStatus(304)
                        return ''
            self.request.response.setHeader(
                'Last-Modified', zope.datetime.rfc1123_date(lmt))
        result = image.openDetached()
        return result

    @property
    def image(self):
        if self.attribute:
            try:
                image = getattr(self.context, self.attribute)
            except AttributeError:
                raise NotFound(self.context, self.attribute, self.request)
        else:
            image = self.context
        return image

    def __call__(self):
        image = self.image
        if image is None:
            return ''

        result = self.renderImage(image)
        return result


class DownloadFile(BrowserView):

    inline = False

    def __call__(self):
        response = self.request.response
        mime = self.context.mimeType
        if mime:
            response.setHeader('Content-Type', mime)
        response.setHeader('Content-Length', self.context.size)
        if self.inline:
            # We don't really accept ranges, but Acrobat Reader will not show the
            # report in the browser page if this header is not provided.
            response.setHeader('Accept-Ranges', 'bytes')
        disposition = self.inline and 'inline' or 'attachment'
        filename = self.context.__name__
        quoted_filename = quoteFilename(filename)
        if quoted_filename:
            disposition += '; filename="%s"' % quoted_filename
        response.setHeader('Content-Disposition', disposition)
        return self.context.openDetached()


