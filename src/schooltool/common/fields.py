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
SchoolTool fields.
"""

import zope.schema
from zope.interface import implements
from zope.file.file import File
from zope.schema import Bytes
from zope.schema.interfaces import TooLong

from schooltool.common import SchoolToolMessage as _


_default = object()


class IImage(zope.schema.interfaces.IBytes):

    size = zope.schema.Tuple(
        title=_(u"Image size"),
        value_type = zope.schema.Int(title=_("Size in pixels")),
        required=False
        )

    format = zope.schema.TextLine(
        title=_(u"Image format"),
        required=True)

    max_file_size = zope.schema.Int(
        title=_(u"Max file size in bytes"),
        default=(10 * (10**6)),
        required=True)


class ImageFile(File):
    """A file that is an image."""


class Image(Bytes):

    implements(IImage)
    _type = ImageFile

    size = None
    format = 'PNG'
    max_file_size = 10 * (10**6)

    def __init__(self, size=_default, format=_default,
                 max_file_size=_default, **kw):
        super(Image, self).__init__(**kw)
        if size is not _default:
            self.size = size
        if format is not _default:
            self.format = format
        if max_file_size is not _default:
            self.max_file_size = max_file_size

    def _validate(self, value):
        if self.max_length is not None and value.size > self.max_length:
            raise TooLong(value, self.max_length)

