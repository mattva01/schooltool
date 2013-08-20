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
SchoolTool flourish zcml directives.
"""
import zope.browserpage.metadirectives
import zope.component.zcml
import zope.configuration.fields
import zope.schema
import zope.security.checker
import zope.viewlet.metadirectives
from zope.interface import Interface
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.publisher.interfaces.browser import IBrowserView

from schooltool.skin.flourish.zcml import IRenderOverrides
from schooltool.skin.flourish.zcml_content import subclass_content, template_specs
from schooltool.skin.flourish.zcml_content import handle_interfaces
from schooltool.skin.flourish.zcml_content import handle_security
from schooltool.skin.flourish.zcml_content import TemplatePath
from schooltool.skin.flourish import interfaces
from schooltool.skin.flourish.report import PDFPage


class IPDFPageDirective(zope.browserpage.metadirectives.IPagesDirective,
                    IRenderOverrides):

    name = zope.schema.TextLine(
        title=u"The name of the PDF (view)",
        required=True,
        )

    title = zope.configuration.fields.MessageID(
        title=u"Title of this PDF",
        required=False,
        )

    author = zope.configuration.fields.MessageID(
        title=u"Author of this PDF",
        description=u"""
        A very short description of this PDF.
        """,
        required=False,
        )

    template = TemplatePath(
        title=u"Main template",
        description=u"""
        Change the main template that renders everything.
        """,
        required=False,
        )

    content_template = TemplatePath(
        title=u"Template for the main PDF content.",
        description=u"""
        Set template that renders main content for this PDF.
        """,
        required=False,
        )


# Arbitrary keys and values are allowed to be passed to the manager.
IPDFPageDirective.setTaggedValue('keyword_arguments', True)


def pdf(_context, name, permission,
        for_=Interface, layer=interfaces.IFlourishLayer,
        title=None, author=None,
        template=None, content_template=None,
        class_=PDFPage,
        update='update', render='render',
        allowed_interface=(), allowed_attributes=(),
        **kwargs
        ):

    forward_methods = {
        'update': update,
        'render': render,
        }

    # BBB: add index to ease porting from old style views
    if (IBrowserView.implementedBy(class_) and
        getattr(class_, 'index', None) is None):
        forward_methods['index'] = render

    if not interfaces.IPDFPage.implementedBy(class_):
        class_ = type(class_.__name__, (class_, PDFPage), {})

    allowed_interface = (tuple(allowed_interface) +
                         (interfaces.IPDFPage, ))

    class_dict = dict(kwargs)
    class_dict['__name__'] = name

    if title is not None:
        class_dict['title'] = title
    if author is not None:
        class_dict['author'] = author

    # XXX: raise ConfigurationError if class_ is PDFPage and
    #      no templates specified

    templates = template_specs({
        'template': template,
        'content_template': content_template,
        }, content_type='xml')

    class_ = subclass_content(
        class_, name,
        forward_methods,
        templates,
        class_dict,
        )

    handle_interfaces(_context, (for_,))
    handle_interfaces(_context, allowed_interface)

    handle_security(class_, permission,
                    allowed_interface, allowed_attributes)

    _context.action(
        discriminator=('view', for_, name, IBrowserRequest, layer),
        callable=zope.component.zcml.handler,
        args=('registerAdapter',
              class_, (for_, layer), Interface, name, _context.info),
        )
