##############################################################################
#
# Copyright (c) 2001, 2002 Zope Corporation and Contributors.
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
"""Placeless Test Setup

$Id$
"""
from zope.testing.cleanup import CleanUp
from zope.component import getGlobalServices
from zope.component.servicenames import Adapters, Utilities, Presentation

# A mix-in class inheriting from CleanUp that also connects the CA services
class PlacelessSetup(CleanUp):

    def setUp(self):
        CleanUp.setUp(self)
        sm = getGlobalServices()
        defineService = sm.defineService
        provideService = sm.provideService

        # utility service
        from zope.component.interfaces import IUtilityService
        defineService(Utilities, IUtilityService)
        from zope.component.utility import GlobalUtilityService
        provideService(Utilities, GlobalUtilityService())

        # adapter service
        from zope.component.interfaces import IAdapterService
        defineService(Adapters, IAdapterService)
        from zope.component.adapter import GlobalAdapterService
        provideService(Adapters, GlobalAdapterService())

        # presentation service
        from zope.component.interfaces import IPresentationService
        defineService(Presentation, IPresentationService)
        from zope.component.presentation import GlobalPresentationService
        provideService(Presentation, GlobalPresentationService())

    def tearDown(self):
        CleanUp.tearDown(self)
