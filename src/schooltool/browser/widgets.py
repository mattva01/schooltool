#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2004 Shuttleworth Foundation
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
Data entry widgets for SchoolTool web application views.

$Id$
"""

import cgi
import datetime

from zope.interface import Interface, Attribute, implements
from schooltool.common import to_unicode
from schooltool.common import parse_date
from schooltool.translation import ugettext as _


__metaclass__ = type


class IWidget(Interface):
    """A widget for data entry.

    A widget deals with two kinds of values -- raw values and processed values
    (for example, a number entry widget's raw value is a text string, and the
    processed value is an int).  A widget uses three functions to deal with
    values: the parser, the validator, and the formatter.  The raw value may be
    None if the request did not contain a field.
    """

    # Widget properies

    css_class = Attribute("CSS class for the widget")

    name = Attribute("Field name")

    label = Attribute("Label")

    unit = Attribute("Text displayed after the widget")

    tabindex = Attribute("Index in tab order")

    # Widget state

    raw_value = Attribute("Raw field value extracted from the request")

    value = Attribute("Processed field value")

    error = Attribute("Error message (optional)")

    # Conversion and validation

    def parser(raw_value):
        "Return a processed value or raise ValueError."

    def formatter(value):
        "Return a raw value."

    def validator(value):
        "Validate the processed value (may raise ValueError)."

    # Methods

    def __call__(tabindex=None):
        """Render the widget into HTML.

        Allows you to override tabindex, if you need it.  (See the page
        template of TimetableSchemaWizard for an example.)

        Returns a unicode string.
        """

    def update(request):
        """Update the value from the request, if it is available.

        May update raw_value, value and error attributes.

        Extracts raw value from the request and calls self.setRawValue, but
        only if the raw value is present in the request (i.e.
        self.getRawValue() is not None).
        """

    def getRawValue(request):
        """Extract the raw value from the request."""

    def setRawValue(raw_value):
        """Set a new value.

        Updates raw_value, value and error attributes.

        Derives value by calling the parser on the raw value, then validates it
        by calling the validator.  If there were no errors, sets self.raw_value
        to a normalized raw value by calling the formatter, and sets self.error
        to None.  If there were errors, sets self.raw_value and puts the error
        message into self.error.
        """

    def setValue(value):
        """Set a new value.

        Updates raw_value, value and error attributes.

        Validates the value by calling the validator.  If there were no errors,
        sets self.raw_value to a normalized raw value by calling the formatter,
        and sets self.error to None.  If there were errors, sets self.raw_value
        to None and puts the error message into self.error.
        """

    def require():
        """Require the value to be supplied.

        If self.raw_value is None, sets self.error.
        """


def defaultParser(raw_value):
    """Default parser for widgets.

    Simply returns raw_value unchanged.

      >>> defaultParser(None)
      >>> defaultParser(u'foo')
      u'foo'

    """
    return raw_value


def defaultValidator(value):
    """Default validator for widgets.

    Accepts all values.

      >>> defaultValidator(None)
      >>> defaultValidator(u'foo')

    """
    pass


def defaultFormatter(value):
    """Default formatter for widgets.

    Converts all values to unicode.

      >>> defaultFormatter(None)
      >>> defaultFormatter(u'foo')
      u'foo'
      >>> defaultFormatter(123)
      u'123'

    """
    if value is None:
        return None
    return unicode(value)


def dateParser(raw_date):
    """Parser for dates.

      >>> dateParser(None)
      >>> dateParser(' ')
      >>> dateParser('1980-02-28')
      datetime.date(1980, 2, 28)
      >>> dateParser('01/02/03')
      Traceback (most recent call last):
        ...
      ValueError: Invalid date.  Please specify YYYY-MM-DD.

    """
    if raw_date is None or not raw_date.strip():
        return None
    try:
        return parse_date(raw_date)
    except ValueError:
        raise ValueError(_("Invalid date.  Please specify YYYY-MM-DD."))


def timeParser(raw_value):
    """Parser for times.

      >>> timeParser(None)
      >>> timeParser(' ')
      >>> timeParser('23:59')
      datetime.time(23, 59)
      >>> timeParser('0:00')
      datetime.time(0, 0)
      >>> timeParser('24:00')
      Traceback (most recent call last):
        ...
      ValueError: Time must be between 00:00 and 24:00.
      >>> timeParser('xyz')
      Traceback (most recent call last):
        ...
      ValueError: Invalid time.  Please specify HH:MM.

    """
    if raw_value is None or not raw_value.strip():
        return None
    try:
        h, m = map(int, raw_value.split(':'))
    except ValueError:
        raise ValueError(_("Invalid time.  Please specify HH:MM."))
    try:
        return datetime.time(h, m)
    except ValueError:
        raise ValueError(_("Time must be between 00:00 and 24:00."))


def timeFormatter(value):
    """Format time without seconds.

      >>> timeFormatter(None)
      >>> timeFormatter(datetime.time(9, 45))
      '9:45'

    """
    if value is None:
        return None
    else:
        return '%d:%02d' % (value.hour, value.minute)


def intParser(raw_value):
    """Parser for intefers.

      >>> intParser(None)
      >>> intParser(' ')
      >>> intParser('1234')
      1234
      >>> intParser('-123')
      -123
      >>> intParser('abc')
      Traceback (most recent call last):
        ...
      ValueError: Invalid value.

    """
    if raw_value is None or not raw_value.strip():
        return None
    try:
        return int(raw_value)
    except ValueError:
        raise ValueError(_("Invalid value."))


def passwordValidator(password):
    r"""Validator for passwords.

    Accepts only ASCII strings.

      >>> passwordValidator(None)
      >>> passwordValidator(u'')
      >>> passwordValidator(u'abc def')
      >>> passwordValidator(u'!@#$%^&*()_+[]{},./<>?;:\"|')

      >>> passwordValidator(u'\u00ff')
      Traceback (most recent call last):
        ...
      ValueError: Password can only contain ASCII characters.

    """
    if not password:
        return
    try:
        unicode(password).encode('ascii')
    except UnicodeError:
        raise ValueError(_("Password can only contain ASCII characters."))


class Widget:
    """Base class for widgets."""

    implements(IWidget)

    css_class = None

    def __init__(self, name, label, parser=None, validator=None,
                 formatter=None, unit=None, value=None, tabindex=None,
                 css_class=None):
        if parser is None:
            parser = defaultParser
        if validator is None:
            validator = defaultValidator
        if formatter is None:
            formatter = defaultFormatter
        self.name = name
        self.label = label
        self.unit = unit
        self.tabindex = tabindex
        self.parser = parser
        self.validator = validator
        self.formatter = formatter
        self.raw_value = None
        self.value = None
        self.error = None
        if css_class is not None: # otherwise inherit class attribute
            self.css_class = css_class
        if value is not None:
            self.setValue(value)

    def __call__(self, tabindex=None):
        raise NotImplementedError('%s did not override Widget.__call__'
                                  % self.__class__.__name__)

    def update(self, request):
        try:
            raw_value = self.getRawValue(request)
        except UnicodeError:
            self.error = _("Invalid UTF-8 data.")
        else:
            if raw_value is not None:
                self.setRawValue(raw_value)

    def getRawValue(self, request):
        if self.name in request.args:
            return to_unicode(request.args.get(self.name)[0])
        else:
            return None

    def setRawValue(self, raw_value):
        try:
            self.value = self.parser(raw_value)
            self.validator(self.value)
        except ValueError, e:
            self.value = None
            self.error = unicode(': '.join(e.args))
            self.raw_value = raw_value
        else:
            self.error = None
            self.raw_value = self.formatter(self.value)

    def setValue(self, value):
        self.value = value
        try:
            self.validator(value)
        except ValueError, e:
            self.error = unicode(': '.join(e.args))
            self.raw_value = None
        else:
            self.error = None
            self.raw_value = self.formatter(self.value)

    def require(self):
        if self.raw_value is None:
            self.error = _("This field is required.")

    def _css_class(self):
        """Helper for subclasses."""
        if self.css_class:
            return ' class="%s"' % cgi.escape(self.css_class, True)
        else:
            return ''

    def _row_class(self):
        """Helper for subclasses."""
        if self.error:
            return ' class="row row_error"'
        else:
            return ' class="row"'

    def _error_html(self):
        """Helper for subclasses."""
        if self.error:
            return '<div class="error">%s</div>\n' % cgi.escape(self.error)
        else:
            return ''

    def _unit_html(self):
        """Helper for subclasses."""
        if self.unit:
            return '<span class="unit">%s</span>\n' % cgi.escape(self.unit)
        else:
            return ''

    def _tabindex_html(self, tabindex=None):
        """Helper for subclasses."""
        if tabindex is None:
            tabindex = self.tabindex
        if tabindex:
            return ' tabindex="%d"' % tabindex
        else:
            return ''


class TextWidget(Widget):
    """Text field widget."""

    implements(IWidget)

    css_class = 'text'

    input_type = 'text'

    def __call__(self, tabindex=None):
        return ('<div%(row_class)s>\n'
                '  <label for="%(name)s">%(label)s</label>\n'
                '  <input%(css_class)s type="%(input_type)s" name="%(name)s"'
                        ' id="%(name)s"%(tabindex)s value="%(value)s" />\n'
                '%(unit)s'
                '%(error)s'
                '</div>' % {'name': cgi.escape(self.name, True),
                            'label': cgi.escape(self.label, True),
                            'input_type': cgi.escape(self.input_type, True),
                            'css_class': self._css_class(),
                            'row_class': self._row_class(),
                            'value': cgi.escape(self.raw_value or '', True),
                            'unit': self._unit_html(),
                            'tabindex': self._tabindex_html(tabindex),
                            'error': self._error_html()})


class PasswordWidget(TextWidget):
    """Password field widget."""

    input_type = 'password'

    def __init__(self, *args, **kw):
        kw.setdefault('validator', passwordValidator)
        TextWidget.__init__(self, *args, **kw)


class TextAreaWidget(Widget):
    """Text area widget.

    Note that TextAreaWidget ignores its 'unit' attribute.
    """

    implements(IWidget)

    css_class = 'text'

    def __call__(self, tabindex=None):
        return ('<div%(row_class)s>\n'
                '  <label for="%(name)s">%(label)s</label>\n'
                '  <textarea%(css_class)s name="%(name)s"'
                        ' id="%(name)s"%(tabindex)s>%(value)s</textarea>\n'
                '%(error)s'
                '</div>' % {'name': cgi.escape(self.name, True),
                            'label': cgi.escape(self.label, True),
                            'css_class': self._css_class(),
                            'row_class': self._row_class(),
                            'value': cgi.escape(self.raw_value or ''),
                            'tabindex': self._tabindex_html(tabindex),
                            'error': self._error_html()})


class SelectionWidget(Widget):
    """Drop-down list widget.

    The constructor accepts an additional argument, choices, which is a
    sequence of tuples (value, display_text).

    Values should be comparable with ==.

    There is a requirement that self.formatter(value) not return None for any
    value listed in choices.

    It is up to self.validator and/or self.parser to ensure that the raw_value
    received from the request corresponds to one of the values in choices.
    """

    implements(IWidget)

    def __init__(self, name, label, choices, parser=None, validator=None,
                 formatter=None, value=None):
        Widget.__init__(self, name, label, parser=parser, validator=validator,
                        formatter=formatter, value=value)
        self.choices = choices

    def __call__(self, tabindex=None):
        options = []
        for value, display in self.choices:
            options.append('    <option value="%(value)s"%(selected)s>'
                           '%(display)s</option>\n'
                           % {'value': cgi.escape(self.formatter(value), True),
                              'display': cgi.escape(display, True),
                              'selected': (value == self.value
                                           and ' selected="selected"'
                                           or '')})
        return ('<div%(row_class)s>\n'
                '  <label for="%(name)s">%(label)s</label>\n'
                '  <select%(css_class)s name="%(name)s"'
                         ' id="%(name)s"%(tabindex)s>\n'
                '%(options)s'
                '  </select>\n'
                '%(unit)s'
                '%(error)s'
                '</div>' % {'name': cgi.escape(self.name, True),
                            'label': cgi.escape(self.label, True),
                            'tabindex': self._tabindex_html(tabindex),
                            'css_class': self._css_class(),
                            'row_class': self._row_class(),
                            'options': ''.join(options),
                            'unit': self._unit_html(),
                            'error': self._error_html()})


class CheckboxWidget(Widget):
    """A checkbox"""

    implements(IWidget)

    def __call__(self, tabindex=None):
        return ('<div%(row_class)s>\n'
                '  <label for="%(name)s">%(label)s</label>\n'
                '  <input %(css_class)s type="checkbox" name="%(name)s"'
                ' id="%(name)s" %(tabindex)s/>\n'
                '%(unit)s'
                '%(error)s'
                '</div>' % {'name': cgi.escape(self.name, True),
                            'label': cgi.escape(self.label, True),
                            'tabindex': self._tabindex_html(tabindex),
                            'css_class': self._css_class(),
                            'row_class': self._row_class(),
                            'unit': self._unit_html(),
                            'error': self._error_html()})
