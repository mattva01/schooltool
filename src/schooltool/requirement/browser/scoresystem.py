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
"""Score System Browser Code

$Id$
"""
__docformat__ = 'reStructuredText'
import zope.interface
import zope.schema
from zope.app import form
from zope.app.pagetemplate import ViewPageTemplateFile

from schooltool import SchoolToolMessage as _
from schooltool.requirement import interfaces, scoresystem

class IWidgetData(interfaces.IRangedValuesScoreSystem):
    """A schema used to generate the score system widget."""

    existing = zope.schema.Choice(
        title=_('Exisiting Score System'),
        vocabulary='schooltool.requirement.scoresystems',
        required=False)

    custom = zope.schema.Bool(
        title=_('Custom score system'),
        required=True)


class WidgetData(object):
    """A simple object used to simulate the widget data."""

    existing = None
    custom = False
    min = 0
    max = 100


class ScoreSystemWidget(object):
    """Score System Widget"""
    zope.interface.implements(form.browser.interfaces.IBrowserWidget,
                              form.interfaces.IInputWidget)

    template = ViewPageTemplateFile('scoresystemwidget.pt')
    _prefix = 'field.'

    # See zope.app.form.interfaces.IWidget
    name = None
    label = property(lambda self: self.context.title)
    hint = property(lambda self: self.context.description)
    visible = True
    # See zope.app.form.interfaces.IInputWidget
    required = property(lambda self: self.context.required)

    def __init__(self, field, request):
        self.context = field
        self.request = request
        data = WidgetData()
        if interfaces.IRequirement.providedBy(field.context):
            ss = field.context.scoresystem
            if scoresystem.ICustomScoreSystem.providedBy(ss):
                data.custom = True
                data.min = ss.min
                data.max = ss.max
            else:
                data.existing = ss
        self.name = self._prefix + field.__name__
        form.utility.setUpEditWidgets(self, IWidgetData, source=data,
                                      prefix=self.name+'.')


    def setRenderedValue(self, value):
        """See zope.app.form.interfaces.IWidget"""
        if scoresystem.ICustomScoreSystem.providedBy(value):
            self.custom_widget.setRenderedValue(True)
            self.min_widget.setRenderedValue(value.min)
            self.max_widget.setRenderedValue(value.max)
        else:
            self.existing_widget.setRenderedValue(value)


    def setPrefix(self, prefix):
        """See zope.app.form.interfaces.IWidget"""
        # Set the prefix locally
        if not prefix.endswith("."):
            prefix += '.'
        self._prefix = prefix
        self.name = prefix + self.context.__name__
        # Now distribute it to the sub-widgets
        for widget in [getattr(self, name+'_widget')
                       for name in zope.schema.getFieldNames(IWidgetData)]:
            widget.setPrefix(self.name+'.')


    def getInputValue(self):
        """See zope.app.form.interfaces.IInputWidget"""
        if self.custom_widget.getInputValue():
            min = self.min_widget.getInputValue()
            max = self.max_widget.getInputValue()
            custom = scoresystem.RangedValuesScoreSystem(
                u'generated', min=min, max=max)
            zope.interface.directlyProvides(
                custom, scoresystem.ICustomScoreSystem)
            return custom
        else:
            return self.existing_widget.getInputValue()


    def applyChanges(self, content):
        """See zope.app.form.interfaces.IInputWidget"""
        field = self.context
        new_value = self.getInputValue()
        old_value = field.query(content, self)
        # The selection of an existing scoresystem has not changed
        if new_value == old_value:
            return False
        # Both, the new and old score system are generated
        if (scoresystem.ICustomScoreSystem.providedBy(new_value) and
            scoresystem.ICustomScoreSystem.providedBy(old_value)):
            # If they both have the same min and max value, then there is no
            # change
            if (new_value.min == old_value.min and
                new_value.max == old_value.max):
                return False

        field.set(content, new_value)
        return True


    def hasInput(self):
        """See zope.app.form.interfaces.IInputWidget"""
        return (self.existing_widget.hasInput() or
                (self.custom_widget.hasValidInput() and
                 self.custom_widget.getInputValue()))


    def hasValidInput(self):
        """See zope.app.form.interfaces.IInputWidget"""
        if (self.custom_widget.hasValidInput() and
            self.custom_widget.getInputValue()):
            return (self.min_widget.hasValidInput() and
                    self.min_widget.hasValidInput())

        return self.existing_widget.hasValidInput()


    def hidden(self):
        """See zope.app.form.browser.interfaces.IBrowserWidget"""
        if (self.custom_widget.hasValidInput() and
            self.custom_widget.getInputValue()):
            output = []
            output.append(self.custom_widget.hidden())
            output.append(self.min_widget.hidden())
            output.append(self.max_widget.hidden())
            return '\n'.join(output)

        return self.existing_widget.hidden()


    def error(self):
        """See zope.app.form.browser.interfaces.IBrowserWidget"""
        custom_error = self.custom_widget.error()
        if custom_error:
            return custom_error
        if (self.custom_widget.hasInput() and
            self.custom_widget.getInputValue()):
            min_error = self.min_widget.error()
            if min_error:
                return min_error
            max_error = self.max_widget.error()
            if max_error:
                return max_error

        return self.existing_widget.error()


    def __call__(self):
        """See zope.app.form.browser.interfaces.IBrowserWidget"""
        return self.template()
