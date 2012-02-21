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
from cStringIO import StringIO
import Image

import zope.formlib.widgets
from zope.component import getUtility, adapter, adapts
from zope.file.file import File
from zope.interface import implementer, Interface, implements
from zope.i18n.interfaces import INegotiator
from zope.traversing.browser.absoluteurl import absoluteURL
from zope.publisher.browser import BrowserView
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


class FileDataURI(BrowserView):

    def __call__(self):
        stream = self.context.open()
        payload = stream.read().encode('base64').replace('\n','')
        stream.close()
        mime = self.context.mimeType
        return 'data:'+mime+';base64,'+payload


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

    SIZE = (99, 132)
    FORMAT = 'JPEG'
    MAX_UPLOAD_SIZE = 10485760 # 10 MB

    def toFieldValue(self, value):
        if value is None or value == '':
            return NOT_CHANGED
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
        if len(data) > self.MAX_UPLOAD_SIZE:
            raise FormatterValidationError(
                _('The image uploaded cannot be larger than 10 MB'), value)
        data = self.processImage(image)
        f = File()
        self.updateFile(f, data)
        return f

    def processImage(self, image):
        kw = {'quality': 100, 'filter': Image.ANTIALIAS}
        result = image
        if image.size != self.SIZE:
            size = self.getMaxSize(image)
            image.thumbnail(size, kw['filter'])
            if image.size != self.SIZE or image.mode == 'RGBA':
                result = Image.new('RGB', self.SIZE, (255, 255, 255))
                left = int(round((self.SIZE[0] - image.size[0])/float(2)))
                up = int(round((self.SIZE[1] - image.size[1])/float(2)))
                mask = None
                if image.mode == 'RGBA':
                    mask = image
                result.paste(image, (left, up), mask)
        f = StringIO()
        result.save(f, self.FORMAT, **kw)
        return f.getvalue()

    def updateFile(self, ob, data):
        ob.mimeType = Image.MIME[self.FORMAT]
        w = ob.open("w")
        w.write(data)
        w.close()

    # XXX: Copied from z3c.image.proc.browser
    def getMaxSize(self, image):
        image_size = image.size
        desired_size = self.SIZE
        x_ratio = float(desired_size[0])/image_size[0]
        y_ratio = float(desired_size[1])/image_size[1]
        if x_ratio < y_ratio:
            new_size = (round(x_ratio*image_size[0]),
                        round(x_ratio*image_size[1]))
        else:
            new_size = (round(y_ratio*image_size[0]),
                        round(y_ratio*image_size[1]))
        return tuple(map(int, new_size))

