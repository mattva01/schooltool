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
SchoolTool flourish widgets.
"""
import re
import os
import sys
import struct
from cStringIO import StringIO
import Image

import zope.formlib.widgets
from zope.component import getUtility, adapter, adapts
from zope.file.file import File
from zope.interface import implementer, Interface, implements
from zope.i18n.interfaces import INegotiator
from zope.traversing.browser.absoluteurl import absoluteURL
from zope.schema.interfaces import IField
from zope.schema import Bytes
from zope.schema._bootstrapinterfaces import TooLong

from z3c.form.browser.file import FileWidget
from z3c.form.interfaces import IFieldWidget, NOT_CHANGED
from z3c.form.widget import ComputedWidgetAttribute, FieldWidget
from z3c.form.converter import FileUploadDataConverter
from z3c.form.converter import FormatterValidationError
import zc.resourcelibrary

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.basicperson.demographics import IDemographicsForm
from schooltool.basicperson.interfaces import IBasicPerson
from schooltool.skin.widgets import FCKConfig
from schooltool.skin.widgets import IFckeditorWidget
from schooltool.skin.widgets import FckeditorFormlibWidget
from schooltool.skin.widgets import FckeditorZ3CFormWidget
from schooltool.skin.flourish.resource import ResourceLibrary
from schooltool.skin.flourish.interfaces import IFlourishLayer
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


Flourish_fckeditor_config = ComputedWidgetAttribute(
    lambda a: FCKConfig(288, 160),
    request=IFlourishLayer,
    widget=IFckeditorWidget,
    )


class FlourishFckeditorScriptBase(object):

    @property
    def script(self):
        zc.resourcelibrary.need("fckeditor")
        config = self.config

        app_url = absoluteURL(ISchoolToolApplication(None), self.request)
        fck_config_path = '%s%s' % (
            app_url, config.path)
        fck_editor_path = '%s/@@/fckeditor/%s/fckeditor/' % (
            app_url, self.fckversion)
        fck_skin_path = '%s/@@/schooltool.skin.flourish-fckeditor/' % (
            app_url)
        fck_editor_css_path = '%s%s' % (fck_skin_path, 'fck_editorarea.css')

        # XXX: using some values that may be not JS safe
        return '''
            <script type="text/javascript" language="JavaScript">
                var %(variable)s = new FCKeditor(
                    "%(id)s", %(width)d, %(height)d, "%(toolbar)s");
                %(variable)s.BasePath = "%(fckBasePath)s";
                %(variable)s.Config["CustomConfigurationsPath"] = "%(customConfigPath)s";
                %(variable)s.Config["SkinPath"] = "%(fckSkinPath)s";
                %(variable)s.Config["EditorAreaCSS"] = "%(fckEditorAreaCSS)s";
                %(variable)s.ReplaceTextarea();
            </script>
            ''' % {
            'id': self.element_id,
            'variable': self.editor_var_name,
            'width': config.width,
            'height': config.height,
            'toolbar': config.toolbar,
            'customConfigPath': fck_config_path,
            'fckBasePath': fck_editor_path,
            'fckSkinPath': fck_skin_path,
            'fckEditorAreaCSS': fck_editor_css_path,
            }


class FlourishFckeditorFormlibWidget(FlourishFckeditorScriptBase,
                                     FckeditorFormlibWidget):

    def __init__(self, *args, **kw):
        super(FlourishFckeditorFormlibWidget, self).__init__(*args, **kw)
        self.config = FCKConfig(288, 160)


class FlourishFckeditorZ3CFormWidget(FlourishFckeditorScriptBase,
                                     FckeditorZ3CFormWidget):

    pass


@adapter(IField, IFlourishLayer)
@implementer(IFieldWidget)
def FlourishFckeditorFieldWidget(field, request):
    return FieldWidget(field, FlourishFckeditorZ3CFormWidget(request))


def is_required_demo_field(adapter):
    field = adapter.field
    return field.required and field.interface is IDemographicsForm


PromptRequiredDemoField = ComputedWidgetAttribute(is_required_demo_field)


class IPhoto(Interface):
    """Marker interface for photos"""


class Photo(Bytes):

    implements(IPhoto)
    _type = File

    def _validate(self, value):
        if self.max_length is not None and value.size > self.max_length:
            raise TooLong(value, self.max_length)


class IPhotoWidget(Interface):
    """Marker for photo widgets"""


class PhotoWidget(FileWidget):

    implements(IPhotoWidget)

    def has_photo(self):
        return IBasicPerson.providedBy(self.context) and \
               self.context.photo is not None


def PhotoFieldWidget(field, request):
    return FieldWidget(field, PhotoWidget(request))


class PhotoDataConverter(FileUploadDataConverter):

    adapts(IPhoto, IPhotoWidget)

    def toFieldValue(self, value):
        if value is None or value == '':
            return NOT_CHANGED
        if value == 'delete':
            # XXX: delete checkbox was marked
            return None
        firstbytes = value.read(1024)
        contentType, width, height = self.getImageInfo(firstbytes)
        if not contentType:
            raise FormatterValidationError(
                _('XXX The file uploaded is not an image XXX'), value)
        value.seek(0)
        data = value.read()
        data = self.processImage(data)
        f = File()
        self.updateFile(f, data, contentType)
        return f

    def processImage(self, data):
        DESIRED_SIZE = (99, 128)
        image = Image.open(StringIO(data))
        kw = {'quality': 100, 'filter': Image.ANTIALIAS}
        transparency = image.info.get('transparency', None)
        if transparency is not None:
            kw['transparency'] = transparency
        if image.size != DESIRED_SIZE:
            size = self.getMaxSize(image.size, DESIRED_SIZE)
            image.thumbnail(size, kw['filter'])
        f = StringIO()
        image.save(f, image.format.upper(), **kw)
        return f.getvalue()

    def updateFile(self, ob, data, mimeType):
        ob.mimeType = mimeType
        w = ob.open("w")
        w.write(data)
        w.close()

    # XXX: Copied from z3c.image.proc.browser
    def getMaxSize(self, image_size, desired_size):
        x_ratio = float(desired_size[0])/image_size[0]
        y_ratio = float(desired_size[1])/image_size[1]
        if x_ratio < y_ratio:
            new_size = (round(x_ratio*image_size[0]),
                        round(x_ratio*image_size[1]))
        else:
            new_size = (round(y_ratio*image_size[0]),
                        round(y_ratio*image_size[1]))
        return tuple(map(int, new_size))

    # XXX: copied from zope.app.file.image
    def getImageInfo(self, data):
        data = str(data)
        size = len(data)
        height = -1
        width = -1
        content_type = ''

        # handle GIFs
        if (size >= 10) and data[:6] in ('GIF87a', 'GIF89a'):
            # Check to see if content_type is correct
            content_type = 'image/gif'
            w, h = struct.unpack("<HH", data[6:10])
            width = int(w)
            height = int(h)

        # See PNG 2. Edition spec (http://www.w3.org/TR/PNG/)
        # Bytes 0-7 are below, 4-byte chunk length, then 'IHDR'
        # and finally the 4-byte width, height
        elif ((size >= 24) and data.startswith('\211PNG\r\n\032\n')
              and (data[12:16] == 'IHDR')):
            content_type = 'image/png'
            w, h = struct.unpack(">LL", data[16:24])
            width = int(w)
            height = int(h)

        # Maybe this is for an older PNG version.
        elif (size >= 16) and data.startswith('\211PNG\r\n\032\n'):
            # Check to see if we have the right content type
            content_type = 'image/png'
            w, h = struct.unpack(">LL", data[8:16])
            width = int(w)
            height = int(h)

        # handle JPEGs
        elif (size >= 2) and data.startswith('\377\330'):
            content_type = 'image/jpeg'
            jpeg = StringIO(data)
            jpeg.read(2)
            b = jpeg.read(1)
            try:
                w = -1
                h = -1
                while (b and ord(b) != 0xDA):
                    while (ord(b) != 0xFF): b = jpeg.read(1)
                    while (ord(b) == 0xFF): b = jpeg.read(1)
                    if (ord(b) >= 0xC0 and ord(b) <= 0xC3):
                        jpeg.read(3)
                        h, w = struct.unpack(">HH", jpeg.read(4))
                        break
                    else:
                        jpeg.read(int(struct.unpack(">H", jpeg.read(2))[0])-2)
                    b = jpeg.read(1)
                width = int(w)
                height = int(h)
            except struct.error:
                pass
            except ValueError:
                pass

        # handle BMPs
        elif (size >= 30) and data.startswith('BM'):
            kind = struct.unpack("<H", data[14:16])[0]
            if kind == 40: # Windows 3.x bitmap
                content_type = 'image/x-ms-bmp'
                width, height = struct.unpack("<LL", data[18:26])

        return content_type, width, height
