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
Browser views for ACLs.

$Id$
"""

from schooltool.browser import View, Template
from schooltool.browser import AppObjectBreadcrumbsMixin
from schooltool.browser.auth import PrivateAccess
from schooltool.component import traverse, getPath
from schooltool.translation import ugettext as _
from schooltool.interfaces import Everybody, ViewPermission
from schooltool.interfaces import AddPermission, ModifyPermission
from schooltool.interfaces import IACL, IPerson, IGroup, ICalendar
from schooltool.browser.widgets import SelectionWidget
from schooltool.browser import absoluteURL

__metaclass__ = type


class ACLView(View, AppObjectBreadcrumbsMixin):
    """Calendar access list view."""

    __used_for__ = IACL

    authorization = PrivateAccess

    template = Template("www/acl.pt")

    def breadcrumbs(self):
        if ICalendar.providedBy(self.context.__parent__):
            owner = self.context.__parent__.__parent__
            breadcrumbs = AppObjectBreadcrumbsMixin.breadcrumbs(self,
                                                                context=owner)
            breadcrumbs.append((_('Calendar'),
                                absoluteURL(self.request, owner.calendar)))
        else:
            owner = self.context.__parent__
            breadcrumbs = AppObjectBreadcrumbsMixin.breadcrumbs(self,
                                                                context=owner)

        breadcrumbs.append((_('ACL'), self.request.uri))
        return breadcrumbs

    def __init__(self, context):
        View.__init__(self, context)

        self.user_widget = SelectionWidget(
            'user', _('User'),
            [(None, _('Select a user'))]
                + self.allUsers() + [(Everybody, _('Everybody'))],
            parser=self.userParser,
            formatter=self.formatUser,
            validator=self.userValidator)

        self.permission_widget = SelectionWidget(
            'permission', _('Permission'),
            [(None, _('Select a permission'))] +
            [(ViewPermission, _('View')),
             (AddPermission, _('Add')),
             (ModifyPermission, _('Modify'))],
            validator=self.permissionValidator,
            formatter=self.formatPermission
            )

    def userParser(self, value):
        if value in (None, ''):
            return value
        elif value == Everybody:
            return Everybody
        try:
           return traverse(self.context, value)
        except TypeError:
           return None

    def formatUser(self, value):
        if value in ('', None):
            return ''
        elif value == Everybody:
            return Everybody
        else:
            return getPath(value)

    def formatPermission(self,  value):
        if not value:
            return ''
        return value

    def userValidator(self, value):
        if (not IPerson.providedBy(value) and not IGroup.providedBy(value) and
            value is not None and value != Everybody):
            raise ValueError(_("Please select a user"))

    def permissionValidator(self, value):
        if value is None:
            return
        if value not in (ViewPermission, AddPermission, ModifyPermission):
            raise ValueError(_("Please select a permission"))

    def list(self):
        """List all grants."""
        grants = []
        for user, permission in self.context:
            if user == Everybody:
                stone = 1 # make it heavy so it ends up at the bottom
                title = _('Everybody')
                value = '%s:%s' % (permission, user)
                url = None
            else:
                stone = 0
                title = user.title
                value = '%s:%s' % (permission, getPath(user))
                url = absoluteURL(self.request, user)
            grants.append((stone, title, {'title': title, 'url': url,
                                          'permission': _(permission),
                                          'value': value}))
        grants.sort()
        return [item for heavy_stone, title, item in grants]

    def allUsers(self):
        """Return a list of objects available for addition"""
        result = []

        for path in ('/persons', '/groups'):
            subresult = [(obj.title, obj)
                         for obj in traverse(self.context, path).itervalues()]
            subresult.sort()
            result += subresult
        return [(obj, title) for title, obj in result]

    def update(self):
        result = []
        self.user_widget.update(self.request)
        self.permission_widget.update(self.request)
        if 'DELETE' in self.request.args:
            for checkbox in self.request.args.get('CHECK', []):
                perm, path = checkbox.split(':', 1)
                if path == Everybody:
                    obj = Everybody
                else:
                    try:
                        obj = traverse(self.context, path)
                    except KeyError:
                        continue
                try:
                    self.context.remove((obj, perm))
                except KeyError:
                    pass
                else:
                    self.request.appLog(
                        _("Revoked permission %s on %s from %s") %
                        (perm, getPath(self.context), self.printUser(obj)))
                    result.append(_("Revoked permission %s from %s") %
                                  (_(perm), self.printUser(obj)))
            return "; ".join(result)

        if 'ADD' in self.request.args:
            self.permission_widget.require()
            self.user_widget.require()

            if not (self.user_widget.error or
                    self.permission_widget.error):
                user = self.user_widget.value
                permission = self.permission_widget.value
                if (user, permission) in self.context:
                    return _("%s already has permission %s") % \
                           (self.printUser(user), _(permission))
                self.context.add((user, permission))
                self.request.appLog(
                    _("Granted permission %s on %s to %s") %
                    (permission, getPath(self.context),
                     self.printUser(user)))
                return _("Granted permission %s to %s") % \
                       (_(permission), self.printUser(user))

    def printUser(self, user):
        if user == Everybody:
            return _('Everybody')
        else:
            return "%s (%s)" % (getPath(user), user.title)
