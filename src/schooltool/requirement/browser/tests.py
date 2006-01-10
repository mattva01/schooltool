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
Tests for group views.

$Id:$
"""

import unittest

from zope.interface import directlyProvides
from zope.publisher.browser import TestRequest
from zope.testing import doctest
from zope.app.traversing.interfaces import IContainmentRoot

from schooltool.app.browser.testing import setUp, tearDown
from schooltool.testing import setup

def doctest_RequirementView():
    r"""Test for RequirementView

    Let's create a view for a requirement:

        >>> from schooltool.requirement.browser.requirement import RequirementView
        >>> from schooltool.requirement.requirement import Requirement
        >>> requirement = Requirement(u"Zope 3 Competencies")
        >>> request = TestRequest()
        >>> view = RequirementView(requirement, request)

    Let's create a tree of subrequirements:

        >>> requirement['subOne'] = Requirement(u"Component Architecture")
        >>> requirement['subOne']['subOne'] = Requirement(u"Component objects")
        >>> requirement['subOne']['subTwo'] = Requirement(u"Adapters")
        >>> requirement['subOne']['subTwo']['subOne'] = Requirement(u"zcml declaration")
        >>> requirement['subOne']['subThree'] = Requirement(u"Interfaces")
        >>> requirement['subTwo'] = Requirement(u"Security")
        >>> requirement['subThree'] = Requirement(u"Testing")

    We can control the depth we display of the tree, but it defaults to three

        >>> view.depth
        3

    This view supports batching.

        >>> view.update()
        >>> requirement['subOne'] in view.batch
        True
        >>> requirement['subTwo'] in view.batch
        True
        >>> requirement['subThree'] in view.batch
        True

    We can also search within the batch using the ``_search`` method
    which even searches recursively through the entire tree structure

        >>> view._search("Inter", requirement)
        [Requirement(u'Interfaces')]
        >>> view._search("zcml", requirement)
        [Requirement(u'zcml declaration')]

    The ``listContentInfo`` method essentially gets another tree structure
    used by the page templates to display each tree node
    """

def doctest_RequirementAddView():
    r"""Test for RequirementAddView

    Adding views in Zope 3 are somewhat unobvious.  The context of an adding
    view is a view named '+' and providing IAdding.

        >>> class AddingStub:
        ...     pass
        >>> context = AddingStub()

    The container to which items will actually be added is accessible as the
    `context` attribute

        >>> from schooltool.requirement.requirement import Requirement
        >>> container = Requirement(u"Test Requirement")
        >>> context.context = container

    ZCML configuration adds some attributes to RequirementAddView, namely
    `schema`, 'fieldNames', and `_factory`.

        >>> from schooltool.requirement.browser.requirement import RequirementAddView
        >>> from schooltool.requirement.interfaces import IRequirement
        >>> from schooltool.requirement.requirement import Requirement
        >>> class RequirementAddViewForTesting(RequirementAddView):
        ...     schema = IRequirement
        ...     fieldNames = ('title',)
        ...     _factory = Requirement

    We can now finally create the view:

        >>> request = TestRequest()
        >>> view = RequirementAddViewForTesting(context, request)

    The `nextURL` method tells Zope 3 where you should be redirected after
    successfully adding a group.  We will pretend that `container` is located
    at the root so that zapi.absoluteURL(container) returns 'http://127.0.0.1'.

        >>> directlyProvides(container, IContainmentRoot)
        >>> view.nextURL()
        'http://127.0.0.1'

    We can cancel an action if we want to:

        >>> request = TestRequest()
        >>> request.form = {'CANCEL': 'Cancel'}
        >>> view = RequirementAddViewForTesting(context, request)
        >>> view.update()
        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('Location')
        'http://127.0.0.1'

    If 'CANCEL' is not present in the request, the view calls inherited
    'update'.  We will use a trick and set update_status to some value to
    short-circuit AddView.update().

        >>> request = TestRequest()
        >>> request.form = {'field.title': 'a_requirement',
        ...                 'UPDATE_SUBMIT': 'Add'}
        >>> view = RequirementAddViewForTesting(context, request)
        >>> view.update_status = 'Just checking'
        >>> view.update()
        'Just checking'

    """


def doctest_RequirementEditView():
    r"""Test for RequirementEditView

    Let's create a view for editing a requirement:

        >>> from schooltool.requirement.browser.requirement import RequirementEditView
        >>> from schooltool.requirement.requirement import Requirement
        >>> from schooltool.requirement.interfaces import IRequirement
        >>> requirement = Requirement(u"Test Requirement")
        >>> directlyProvides(requirement, IContainmentRoot)
        >>> request = TestRequest()

        >>> class TestRequirementEditView(RequirementEditView):
        ...     schema = IRequirement
        ...     fieldNames = ('title',)
        ...     _factory = Requirement

        >>> view = TestRequirementEditView(requirement, request)

    We should not get redirected if we did not click on apply button:

        >>> request = TestRequest()
        >>> view = TestRequirementEditView(requirement, request)
        >>> view.update()
        ''
        >>> request.response.getStatus()
        599

    After changing name of the requirement you should get redirected to the requirement
    list:

        >>> request = TestRequest()
        >>> request.form = {'UPDATE_SUBMIT': 'Apply',
        ...                 'field.title': u'new_title'}
        >>> view = TestRequirementEditView(requirement, request)
        >>> view.update()
        u'Updated on ${date_time}'
        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('Location')
        'http://127.0.0.1'

        >>> requirement.title
        u'new_title'

    Even if the title has not changed you should get redirected to the requirement
    list:

        >>> request = TestRequest()
        >>> request.form = {'UPDATE_SUBMIT': 'Apply',
        ...                 'field.title': u'new_title'}
        >>> view = TestRequirementEditView(requirement, request)
        >>> view.update()
        ''
        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('Location')
        'http://127.0.0.1'

        >>> requirement.title
        u'new_title'

    We should not get redirected if there were errors:

        >>> request = TestRequest()
        >>> request.form = {'UPDATE_SUBMIT': 'Apply',
        ...                 'field.title': u''}
        >>> view = TestRequirementEditView(requirement, request)
        >>> view.update()
        u'An error occurred.'
        >>> request.response.getStatus()
        599

        >>> requirement.title
        u'new_title'

    We can cancel an action if we want to:

        >>> request = TestRequest()
        >>> request.form = {'CANCEL': 'Cancel'}
        >>> view = TestRequirementEditView(requirement, request)
        >>> view.update()
        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('Location')
        'http://127.0.0.1'

    """

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                       optionflags=doctest.ELLIPSIS|
                                                   doctest.REPORT_NDIFF))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
