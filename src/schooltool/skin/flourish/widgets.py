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

import zope.formlib.widgets
from zope.component import getUtility, adapter
from zope.interface import implementer
from zope.i18n.interfaces import INegotiator
from zope.traversing.browser.absoluteurl import absoluteURL
from zope.schema.interfaces import IField

from z3c.form.interfaces import IFieldWidget
from z3c.form.widget import ComputedWidgetAttribute, FieldWidget
import zc.resourcelibrary

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.skin.widgets import FCKConfig
from schooltool.skin.widgets import IFckeditorWidget
from schooltool.skin.widgets import FckeditorFormlibWidget
from schooltool.skin.widgets import FckeditorZ3CFormWidget
from schooltool.skin.flourish.resource import ResourceLibrary
from schooltool.skin.flourish.interfaces import IFlourishLayer


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
