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


Initial School Setup
--------------------

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

Next the administrator defines the courses that are available in the school.

    >>> manager.getLink('Courses').click()
    >>> manager.getLink('New Course').click()
    >>> manager.getControl('Title').value = 'Physics I'
    >>> manager.getControl('Add').click()
    >>> manager.getLink('Physics I').click()

In this particular case, the school also wants to mandate that the teacher
always has to write a final exam in Physics I. In terms of SchoolTool this
means that we need to add an activity:

    >>> manager.getLink('Activities').click()

    >>> manager.getLink('New Activity').click()
    >>> manager.getControl('Title').value = 'Final'
    >>> manager.getControl('Description').value = 'Final Exam'
    >>> manager.getControl('Category').value = ['exam']
    >>> manager.getControl(
    ...     name='field.scoresystem.existing').value = ['100 Points']
    >>> manager.getControl('Add').click()

    >>> 'Final' in manager.contents
    True

This completes the initial school setup.


Term Setup
----------

Every term, the administrators of a school are going to setup sections. So
let's add a section for our course:

    >>> manager.getLink('Courses').click()
    >>> manager.getLink('Physics I').click()

    >>> manager.getLink('New Section').click()
    >>> manager.getControl('Code').value = 'PHYI-1'
    >>> manager.getControl('Description').value = 'Section 1'
    >>> manager.getControl('Add').click()

But what would a section be without some students and a teacher?

    >>> manager.getLink('Persons').click()

    >>> manager.getLink('New Person').click()
    >>> manager.getControl('Full name').value = 'Paul Cardune'
    >>> manager.getControl('Username').value = 'paul'
    >>> manager.getControl('Password').value = 'pwd'
    >>> manager.getControl('Verify password').value = 'pwd'
    >>> manager.getControl('Students').click()
    >>> manager.getControl('Add').click()

    >>> manager.getLink('New Person').click()
    >>> manager.getControl('Full name').value = 'Tom Hoffman'
    >>> manager.getControl('Username').value = 'tom'
    >>> manager.getControl('Password').value = 'pwd'
    >>> manager.getControl('Verify password').value = 'pwd'
    >>> manager.getControl('Students').click()
    >>> manager.getControl('Add').click()

    >>> manager.getLink('New Person').click()
    >>> manager.getControl('Full name').value = 'Claudia Richter'
    >>> manager.getControl('Username').value = 'claudia'
    >>> manager.getControl('Password').value = 'pwd'
    >>> manager.getControl('Verify password').value = 'pwd'
    >>> manager.getControl('Students').click()
    >>> manager.getControl('Add').click()

    >>> manager.getLink('New Person').click()
    >>> manager.getControl('Full name').value = 'Stephan Richter'
    >>> manager.getControl('Username').value = 'stephan'
    >>> manager.getControl('Password').value = 'pwd'
    >>> manager.getControl('Verify password').value = 'pwd'
    >>> manager.getControl('Teachers').click()
    >>> manager.getControl('Add').click()

Now we can add those people to the section:

    >>> manager.getLink('Courses').click()
    >>> manager.getLink('Physics I').click()
    >>> manager.getLink('(PHYI-1)').click()

    >>> manager.getLink('edit individuals').click()
    >>> manager.getControl('Paul Cardune').click()
    >>> manager.getControl('Tom Hoffman').click()
    >>> manager.getControl('Claudia Richter').click()
    >>> manager.getControl('Apply').click()

    >>> 'Paul Cardune' in manager.contents
    True

    >>> manager.getLink('edit instructors').click()
    >>> manager.getControl('Stephan Richter').click()
    >>> manager.getControl('Add').click()
    >>> manager.getControl('Cancel').click()

The instructor must also receive management access to the section in order to
manipulate activities and other section data:

    >>> manager.getLink('Set Up Access').click()
    >>> manager.getControl(name='sb.person.stephan').value = [
    ...     'schooltool.viewCalendar', 'schooltool.view',
    ...     'schooltool.edit', 'schooltool.create']
    >>> manager.getControl('Set Access', index=0).click()


Grading
-------

Once the term started, the instructor of the section will add more activities:

    >>> stephan = Browser()
    >>> stephan.open('http://localhost/')
    >>> stephan.getLink('Log In').click()
    >>> stephan.getControl('Username').value = 'stephan'
    >>> stephan.getControl('Password').value = 'pwd'
    >>> stephan.getControl('Log in').click()

    >>> stephan.getLink('top').click()
    >>> stephan.getLink('Courses').click()
    >>> stephan.getLink('Physics I').click()
    >>> stephan.getLink('(PHYI-1)').click()
    >>> stephan.getLink('Activities').click()

Note that the final is already listed:

    >>> 'Final' in stephan.contents
    True

    >>> stephan.getLink('New Activity').click()
    >>> stephan.getControl('Title').value = 'HW 1'
    >>> stephan.getControl('Description').value = 'Homework 1'
    >>> stephan.getControl('Category').value = ['assignment']
    >>> stephan.getControl(
    ...     name='field.scoresystem.existing').value = ['100 Points']
    >>> stephan.getControl('Add').click()
    >>> 'HW 1' in stephan.contents
    True

    >>> stephan.getLink('New Activity').click()
    >>> stephan.getControl('Title').value = 'HW 2'
    >>> stephan.getControl('Description').value = 'Homework 2'
    >>> stephan.getControl('Category').value = ['assignment']
    >>> stephan.getControl(
    ...     name='field.scoresystem.existing').value = ['100 Points']
    >>> stephan.getControl('Add').click()
    >>> 'HW 2' in stephan.contents
    True

XXX Edit form test later, once we can have custom scoresystems.

Nore that we have both, students and activities, we can enter the gradebook.

    >>> stephan.getLink('top').click()
    >>> stephan.getLink('Courses').click()
    >>> stephan.getLink('Physics I').click()
    >>> stephan.getLink('(PHYI-1)').click()
    >>> stephan.getLink('Gradebook').click()

The initial gradebook screen is a simple spreadsheet. In order to prevent
accidental score submission, we do not allow to enter grades in this
table. Instead you select a row (student), column (activity) or cell (student,
activity) to enter the scores.


Entering Scores for a Row (Student)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Let's say we want to enter the grades for Claudia. All we do is to simply
click on her name:

    >>> stephan.getLink('Claudia Richter').click()

Now we just enter the grades:

    >>> stephan.getControl('Final').value = u'93'
    >>> stephan.getControl('HW 1').value = u'87'
    >>> stephan.getControl('HW 2').value = u'56'

    >>> stephan.getControl('Update').click()

The screen will return to the grade overview, where the grades are no visible:

    >>> '93' in stephan.contents
    True
    >>> '87' in stephan.contents
    True
    >>> '56' in stephan.contents
    True

Now let's enter again and change a grade:

    >>> stephan.getLink('Claudia Richter').click()
    >>> stephan.getControl('HW 2').value = u'76'
    >>> stephan.getControl('Update').click()

    >>> '76' in stephan.contents
    True

Of course, you can also abort the grading.

    >>> stephan.getLink('Claudia Richter').click()
    >>> stephan.getControl('Cancel').click()
    >>> stephan.url
    'http://localhost/sections/phyi1/gradebook/index.html'


Entering Scores for a Column (Activity)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Let's say we want to enter the grades for Homework 1. All we do is to simply
click on the activity's name:

    >>> stephan.getLink('HW 1').click()

Now we just enter the grades. Since Claudia has already a grade, we only need
to grade Paul and Tom:

    >>> stephan.getControl('Paul Cardune').value = u'90'
    >>> stephan.getControl('Tom Hoffman').value = u'82'

    >>> stephan.getControl('Update').click()

The screen will return to the grade overview, where the grades are no visible:

    >>> '90' in stephan.contents
    True
    >>> '82' in stephan.contents
    True

Now let's enter again and change a grade:

    >>> stephan.getLink('HW 1').click()
    >>> stephan.getControl('Claudia Richter').value = u'98'
    >>> stephan.getControl('Update').click()

    >>> '98' in stephan.contents
    True

Of course, you can also abort the grading.

    >>> stephan.getLink('HW 1').click()
    >>> stephan.getControl('Cancel').click()
    >>> stephan.url
    'http://localhost/sections/phyi1/gradebook/index.html'


Entering Scores for a Cell (Student, Activity)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When you click directly on the grade, you can also edit it. Let's day that we
want to modify Claudia's Homework 2 grade. Until now she had a 76:

    >>> stephan.getLink('76').click()

The screen that opens gives you several pieces of information, such as the
student's name,

    >>> 'Claudia Richter' in stephan.contents
    True

the activity name,

    >>> 'HW 2' in stephan.contents
    True

the (due) date of the activity,

    # Cannot show the value because it is variable
    >>> '(Due) Date' in stephan.contents
    True

the last modification date,

    # Cannot show the value because it is variable
    >>> 'Modification Date' in stephan.contents
    True

and the maximum score:

    >>> '100' in stephan.contents
    True

This for also allows you to delete the evaluation, which is sometimes
necessary:

    >>> stephan.getControl('Grade').value
    '76'
    >>> stephan.getControl('Delete').click()
    >>> stephan.getControl('Grade').value
    ''

Now let's enter a new grade:

    >>> stephan.getControl('Grade').value = '86'
    >>> stephan.getControl('Update').click()

    >>> stephan.url
    'http://localhost/sections/phyi1/gradebook/index.html'
    >>> '86' in stephan.contents
    True

Of course, you can also cancel actions:

    >>> stephan.getLink('86').click()
    >>> stephan.getControl('Grade').value = '66'
    >>> stephan.getControl('Cancel').click()

    >>> stephan.url
    'http://localhost/sections/phyi1/gradebook/index.html'
    >>> '86' in stephan.contents
    True
