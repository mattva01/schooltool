#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003 Shuttleworth Foundation
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
Checks for the unit tests.
"""

import sys

__metaclass__ = type


def warn(msg):
    print >> sys.stderr, msg


class ComponentChecks:

    def startTest(self, test):
        from schooltool import component
        self.facet_factory_registry = dict(component.facet_factory_registry)
        self.uri_registry = dict(component._uri_registry)
        self.relationship_registry = dict(component.relationship_registry._reg)
        self.view_registry = dict(component.view_registry._reg)

    def stopTest(self, test):
        from schooltool import component
        if self.facet_factory_registry != component.facet_factory_registry:
            warn("%s changed facet factory registry" % test)
        if self.uri_registry != component._uri_registry:
            warn("%s changed URI registry" % test)
        if self.relationship_registry != component.relationship_registry._reg:
            warn("%s changed relationship registry" % test)
        if self.view_registry != component.view_registry._reg:
            warn("%s changed view registry" % test)


class TransactionChecks:

    def startTest(self, test):
        import zodb.ztransaction # calls transaction.set_factory
        from transaction import get_transaction
        txn = get_transaction()
        self.had_resources = bool(txn._resources)

    def stopTest(self, test):
        if self.had_resources:
            return
        from transaction import get_transaction
        txn = get_transaction()
        if txn._resources:
            warn("%s left an unclean transaction" % test)


def test_hooks():
    return [ComponentChecks(), TransactionChecks()]
