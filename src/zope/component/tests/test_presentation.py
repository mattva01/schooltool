##############################################################################
#
# Copyright (c) 2003 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Presentation Serivce tests

$Id$
"""
import unittest
from doctest import DocTestSuite
from zope.component.presentation import GlobalPresentationService
import zope.interface

class IRequest(zope.interface.Interface):
    "Demonstration request type"

class Request(object):
    zope.interface.implements(IRequest)
    def getPresentationSkin(self):
        return getattr(self, 'skin', None)

class IContact(zope.interface.Interface):
    "Demonstration content type"

class Contact(object):
    zope.interface.implements(IContact)

class MyView(object):
    def __init__(self, context, request):
        self.context, self.request = context, request


def test_view_lookup_fails_w_wrong_skin():
    """
    >>> s = GlobalPresentationService()
    >>> s.defineLayer('custom')
    >>> s.defineSkin('custom', ['custom', 'default'])

    >>> request = Request()

    >>> s.provideAdapter(IRequest, MyView, contexts=[IContact], name='foo',
    ...                  layer='custom')

    >>> c = Contact()

    >>> s.queryView(c, 'foo', request)

    We don't get anothing because we registered in the custom layer,
    but looked up in the default skin which has only the default layer.
    """

class ICompany(zope.interface.Interface):
    "Demonstration content type"

class Company(object):
    zope.interface.implements(ICompany)

class ContactInCompanyView:
    def __init__(self, contact, company, request):
        self.contact, self.company, self.request = contact, company, request

class IFamily(zope.interface.Interface):
    "Demonstration content type"

class Family(object):
    zope.interface.implements(IFamily)

class ContactInFamilyView(object):
    def __init__(self, contact, family, request):
        self.contact, self.family, self.request = contact, family, request

def test_multi_views():
    """A multi-view is a view on multiple objects

    >>> s = GlobalPresentationService()
    >>> request = Request()

    >>> s.provideAdapter(IRequest, ContactInCompanyView,
    ...                  contexts=[IContact, ICompany], name='foo',
    ...                  info='test 1')

    >>> bob = Contact()
    >>> acme = Company()

    >>> v = s.queryMultiView((bob, acme), request, name='foo')
    >>> v.__class__.__name__
    'ContactInCompanyView'
    >>> v.contact is bob
    True
    >>> v.company is acme
    True
    >>> v.request is request
    True

    >>> s.provideAdapter(IRequest, ContactInFamilyView,
    ...                  contexts=[IContact, IFamily], name='foo',
    ...                  info='test 2')

    >>> smith = Family()
    >>> v = s.queryMultiView((bob, smith), request, name='foo')
    >>> v.__class__.__name__
    'ContactInFamilyView'
    >>> v.contact is bob
    True
    >>> v.family is smith
    True
    >>> v.request is request
    True

    Provided adapters (views and resources) are recorded as registrations:

    >>> registrations = map(str, s.registrations())
    >>> registrations.sort()
    >>> for r in registrations:
    ...     print r
    zope.component.presentation.PresentationRegistration(""" \
       """default, ('IContact', 'ICompany', 'IRequest'), """ \
       """'Interface', 'foo', 'ContactInCompanyView', 'test 1')
    zope.component.presentation.PresentationRegistration(""" \
       """default, ('IContact', 'IFamily', 'IRequest'), """ \
       """'Interface', 'foo', 'ContactInFamilyView', 'test 2')

    """

def test_provideView():
    """

    The provideView is a simpler and backward-compatible interface to
    provideAdapter.

    >>> s = GlobalPresentationService()
    >>> request = Request()
    >>> s.provideView(IContact, 'foo', IRequest, MyView)


    >>> c = Contact()
    >>> v = s.queryView(c, 'foo', request)
    >>> v.__class__.__name__
    'MyView'
    >>> v.request is request
    True
    >>> v.context is c
    True

    We can specify a layer and we can provide a view factory directly:

    >>> s.defineLayer('custom')
    >>> s.defineSkin('custom', ['custom', 'default'])
    >>> s.provideView(IContact, 'index.html', IRequest, MyView, layer='custom')

    >>> c = Contact()
    >>> request.skin = 'custom'

    >>> v = s.queryView(c, 'foo', request)

    >>> v.__class__.__name__
    'MyView'
    >>> v.request is request
    True
    >>> v.context is c
    True
    """


def test_default_view_names():
    """
    >>> s = GlobalPresentationService()
    >>> request = Request()
    >>> c = Contact()

    We haven't set a default view name:

    >>> s.queryDefaultViewName(c, request)

    Let's set a "default default":

    >>> s.setDefaultViewName(None, IRequest, 'index.html')

    And then we'll get it is we look something up:

    >>> s.queryDefaultViewName(c, request)
    'index.html'

    Now we'll set a name for a specific interface. We'll also specify
    a specifioc layer:

    >>> s.defineLayer('custom')
    >>> s.defineSkin('custom', ['custom', 'default'])
    >>> s.setDefaultViewName(IContact, IRequest, 'hello.html', layer='custom')

    If we don't specify the custum skin, we'll still get the default:

    >>> s.queryDefaultViewName(c, request)
    'index.html'

    But if we specify a custom skin, we'll get the custom value for a contact:

    >>> request.skin = 'custom'
    >>> s.queryDefaultViewName(c, request)
    'hello.html'

    But not for something else:

    >>> s.queryDefaultViewName(42, request)
    'index.html'

    """

def test_default_skin_affects_lookup():
    """
    >>> s = GlobalPresentationService()
    >>> s.defineLayer('custom')
    >>> s.defineSkin('custom', ['custom', 'default'])

    >>> request = Request()

    >>> class MyResource(object):
    ...    def __init__(self, request):
    ...        self.request = request
    >>> s.provideAdapter(IRequest, MyResource, name='foo', layer='custom')
    >>> s.queryResource('foo', request)

    >>> s.provideAdapter(IRequest, MyView, contexts=[IContact], name='foo',
    ...                  layer='custom')

    >>> c = Contact()
    >>> v = s.queryView(c, 'foo', request)


    >>> s.setDefaultSkin('custom')


    >>> r = s.queryResource('foo', request)
    >>> r.__class__.__name__
    'MyResource'
    >>> r.request is request
    True

    >>> v = s.queryView(c, 'foo', request)
    >>> v.__class__.__name__
    'MyView'
    >>> v.request is request
    True
    >>> v.context is c
    True
    """

def test_pickling():
    """
    >>> from zope.component.tests.test_service import testServiceManager
    >>> from zope.component.interfaces import IPresentationService
    >>> testServiceManager.defineService('Presentation', IPresentationService)
    >>> presentation = GlobalPresentationService()
    >>> testServiceManager.provideService('Presentation', presentation)
    >>> import pickle

    >>> s = pickle.loads(pickle.dumps(presentation))
    >>> s is presentation
    True

    >>> layer = pickle.loads(pickle.dumps(presentation.queryLayer('default')))
    >>> (layer is presentation.queryLayer('default')) and (layer is not None)
    True

    >>> testServiceManager._clear()
    """


def test_suite():
    return unittest.TestSuite((
        DocTestSuite('zope.component.presentation'),
        DocTestSuite(),
        ))

if __name__ == '__main__': unittest.main()
