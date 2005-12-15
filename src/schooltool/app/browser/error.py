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
SchoolBell internal error view.

$Id$
"""

import sys
import linecache
import cgi

from zope.interface import implements
from zope.app.publisher.browser import BrowserView
from zope.app.exception.interfaces import ISystemErrorView


class ErrorView(BrowserView):
    """A view for server error messages."""

    implements(ISystemErrorView)

    def isSystemError(self):
        return True

    def __call__(self):
        self.request.response.setStatus(500)
        return self.index()

    def traceback(self):
        # Note: this function exposes filenames to the web user; some may
        # consider it a security risk.
        etype, value, tb = sys.exc_info()
        lines = []
        w = lines.append
        q = lambda s: cgi.escape(str(s), True)
        for filename, lineno, method, locals in extract_tb(tb):
            w('File "<span class="filename">%s</span>",'
                    ' line <span class="lineno">%s</span>,'
                    ' in <span class="method">%s</span>\n'
              % (q(filename), q(lineno), q(method)))
            w('  <span class="source">%s</span>\n'
              % q(linecache.getline(filename, lineno).strip()))
            self._extra_info(w, dict(locals))
        return "".join(lines)

    def _extra_info(self, w, locals):
        # TODO: unit tests would be nice
        q = lambda s: cgi.escape(str(s), True)
        if '__traceback_info__' in locals:
            tb_info = locals['__traceback_info__']
            w('Extra information: %s\n' % q(repr(tb_info)))
        if '__traceback_supplement__' in locals:
            tb_supplement = locals['__traceback_supplement__']
            tb_supplement = tb_supplement[0](*tb_supplement[1:])
            from zope.pagetemplate.pagetemplate import \
                    PageTemplateTracebackSupplement
            from zope.tales.tales import TALESTracebackSupplement
            if isinstance(tb_supplement, PageTemplateTracebackSupplement):
                source_file = tb_supplement.manageable_object.pt_source_file()
                if source_file:
                    w('Template "<span class="filename">%s</span>"\n'
                      % q(source_file))
            elif isinstance(tb_supplement, TALESTracebackSupplement):
                w('Template "<span class="filename">%s</span>",'
                  ' line <span class="lineno">%s</span>,'
                  ' column <span class="column">%s</span>\n'
                  % (q(tb_supplement.source_url), q(tb_supplement.line),
                     q(tb_supplement.column)))
                w('  Expression: <span class="expr">%s</span>\n'
                  % q(tb_supplement.expression))
            else:
                w('__traceback_supplement__ = %s\n'
                  % q(repr(tb_supplement)))


def extract_tb(tb, limit=None):
    """Improved version of traceback.extract_tb.

    Includes a dict with locals in every stack frame instead of the line.
    """
    # TODO: unit tests would be nice
    list = []
    while tb is not None and (limit is None or len(list) < limit):
        frame = tb.tb_frame
        code = frame.f_code
        name = code.co_name
        filename = code.co_filename
        lineno = tb.tb_lineno
        locals = frame.f_locals
        list.append((filename, lineno, name, locals))
        tb = tb.tb_next
    return list
