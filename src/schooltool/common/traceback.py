#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2013 Shuttleworth Foundation
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

import cgi
import linecache


def extract_traceback(tb, limit=None):
    """Improved version of traceback.extract_tb.

    Includes a dict with locals in every stack frame instead of the line.
    """
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


def format_html_exception(etype, exception, traceback):
    # Note: this function exposes filenames to the web user; some may
    # consider it a security risk.
    lines = []
    out = lines.append
    out('<h2>Exception</h2>\n')
    out('<pre>\n')
    format_html_ex(out, exception)
    out('</pre>\n')
    out('<h2>Traceback</h2>\n')
    out('<pre>\n')
    format_html_traceback(out, traceback)
    out('</pre>\n')
    return "".join(lines)


def format_html_ex(out, exception):
    escape = lambda s: cgi.escape(str(s), True)
    lines = str(exception).strip().splitlines()
    for line in lines:
        out('<span>%s</span>\n' % escape(line))


def format_html_traceback(out, traceback):
    escape = lambda s: cgi.escape(str(s), True)
    extracted = extract_traceback(traceback)
    for filename, lineno, method, locals in extracted:
        out('File "<span class="filename">%s</span>",'
            ' line <span class="lineno">%s</span>,'
            ' in <span class="method">%s</span>\n'
            % (escape(filename), escape(lineno), escape(method)))
        out('  <span class="source">%s</span>\n'
          % escape(linecache.getline(filename, lineno).strip()))
        extra_info_html(out, dict(locals))


def extra_info_html(out, locals):
    escape = lambda s: cgi.escape(str(s), True)
    if '__traceback_info__' in locals:
        tb_info = locals['__traceback_info__']
        out('Extra information: %s\n' % escape(repr(tb_info)))
    if '__traceback_supplement__' in locals:
        tb_supplement = locals['__traceback_supplement__']
        tb_supplement = tb_supplement[0](*tb_supplement[1:])
        from zope.pagetemplate.pagetemplate import \
                PageTemplateTracebackSupplement
        from zope.tales.tales import TALESTracebackSupplement
        if isinstance(tb_supplement, PageTemplateTracebackSupplement):
            source_file = tb_supplement.manageable_object.pt_source_file()
            if source_file:
                out('Template "<span class="filename">%s</span>"\n'
                  % escape(source_file))
        elif isinstance(tb_supplement, TALESTracebackSupplement):
            out('Template "<span class="filename">%s</span>",'
              ' line <span class="lineno">%s</span>,'
              ' column <span class="column">%s</span>\n'
              % (escape(tb_supplement.source_url), escape(tb_supplement.line),
                 escape(tb_supplement.column)))
            out('  Expression: <span class="expr">%s</span>\n'
              % escape(tb_supplement.expression))
        else:
            out('__traceback_supplement__ = %s\n'
              % escape(repr(tb_supplement)))
