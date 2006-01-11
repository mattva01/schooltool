===========================
Requirements via the Web UI
===========================

This document presents the mangagement of requirements from the perspective
of the Web UI.

    >>> from zope.testbrowser import Browser
    >>> browser = Browser()
    >>> browser.addHeader('Authorization', 'Basic manager:schooltool')

    >>> browser.handleErrors = False
    >>> browser.open('http://localhost/')


Requirement Management
----------------------

Requirements are accessed using the requirement namespace.  The namespace can
be used on anything that has been configured to implement IHaveRequirement 
First we will look at global requirements, which are attached to the
``SchoolToolApplication`` object.  From this screen we can add subrequirements.

    >>> browser.open('http://localhost/++requirement++')
    >>> 'SchoolTool Sub Requirements' in browser.contents
    True

    >>> browser.getLink('New Requirement').click()
    >>> browser.getControl('Title').value = u'Citizenship'
    >>> browser.getControl('Add').click()

    >>> 'Citizenship' in browser.contents
    True

We can then navigate to this new requirement and edit it.

    >>> browser.getLink('Citizenship').click()
    >>> 'Citizenship Sub Requirements' in browser.contents
    True

    >>> browser.getLink('Edit Requirement').click()
    >>> browser.getControl('Title').value = u'Being a Good Citizen'
    >>> browser.getControl('Apply').click()
    >>> 'Being a Good Citizen Sub Requirements' in browser.contents
    True

If we create a sub requirement within this one, it will show up in the
top level requirement, because the page recurses down the requirement tree.

    >>> browser.getLink('New Requirement').click()
    >>> browser.getControl('Title').value = u'Be kind to your fellow students.'
    >>> browser.getControl('Add').click()

    >>> browser.open('http://localhost/++requirement++')
    >>> 'Be kind to your fellow students.' in browser.contents
    True

The view defaults to showing a depth of 3 recurssions.  If we want to show
only the ones directly under the top level, we can use the depth control.

    >>> browser.getControl('2').name
    'DEPTH'
    >>> browser.getControl('2').click()
    >>> browser.getControl('1').click()
    >>> 'Be kind to your fellow students.' not in browser.contents
    True
