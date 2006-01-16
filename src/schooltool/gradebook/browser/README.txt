=============
The Gradebook
=============

There are many tasks that are involved in setting up and using a
gradebook. The first task the administrator has to complete during the
SchoolTool setup is the configuration of the categories. So let's log in as a
manager:

    >>> from zope.testbrowser import Browser

    >>> manager = Browser()
    >>> manager.open('http://localhost/')
    >>> manager.getLink('Log In').click()
    >>> manager.getControl('Username').value = 'manager'
    >>> manager.getControl('Password').value = 'schooltool'
    >>> manager.getControl('Log in').click()

We now go to the top and enter the category management page:

    >>> manager.getLink('top').click()
    >>> manager.getLink('Activity Categories').click()

As you can see, there are already several categories pre-defined. Oftentimes,
those categories do not work for a school. Either you do not need some and/or
others are missing. So let's start by deleting a couple of categories:

    >>> 'essay' in manager.contents
    True
    >>> 'journal' in manager.contents
    True

    >>> manager.getControl(name='field.categories:list').value = [
    ...     'essay', 'journal', 'homework', 'presentation']
    >>> manager.getControl('Remove').click()

    >>> 'essay' in manager.contents
    False
    >>> 'journal' in manager.contents
    False

Next, we add a new category:

    >>> 'Lab Report' in manager.contents
    False

    >>> manager.getControl('New Category').value = 'Lab Report'
    >>> manager.getControl('Add').click()

    >>> 'Lab Report' in manager.contents
    True

We can also change the default category:

    >>> manager.getControl('Default Category').value
    ['assignment']

    >>> manager.getControl('Default Category').value = ['exam']
    >>> manager.getControl('Change').click()

    >>> manager.getControl('Default Category').value
    ['exam']

