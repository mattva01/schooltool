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

    >>> manager.getLink('SchoolTool').click()
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


Gradbook Management
-------------------

Once the term started, the instructor of the section will add more activities:

    >>> stephan = Browser()
    >>> stephan.open('http://localhost/')
    >>> stephan.getLink('Log In').click()
    >>> stephan.getControl('Username').value = 'stephan'
    >>> stephan.getControl('Password').value = 'pwd'
    >>> stephan.getControl('Log in').click()

    >>> stephan.getLink('SchoolTool').click()
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

But, oh, we really did not want to make Homework 2 out of a hundred points,
but only out of 50. So let's edit it:

    >>> stephan.getLink('HW 2').click()
    >>> stephan.getControl('Custom score system').click()
    >>> stephan.getControl('Maximum').value = '50'
    >>> stephan.getControl('Apply').click()

    >>> stephan.getControl('Maximum').value
    '50'
    >>> stephan.getLink('Activities').click()

Now that we have all our activities setup, we would like to rearrange their
order more logically. The final should really be at the end of the list. In
the browser you should usually just select the new position and some
Javascript would submit the form. Since Javascript is not working in the
tests, we submit, the form manually:

    >>> stephan.open(stephan.url+'?form-submitted=&pos.Activity=3')
    >>> stephan.contents.find('HW 1') \
    ...     < stephan.contents.find('HW 2') \
    ...     < stephan.contents.find('Final')
    True

Also note that the final cannot be edited, since it is inherited:

    >>> stephan.getLink('Final')
    Traceback (most recent call last):
    ...
    LinkNotFoundError

    >>> stephan.getLink('HW 1')
    <Link text='HW 1' url='.../sections/phyi1/activities/Activity-2'>

Finally, you can also delete activities that you have locally created:

    >>> stephan.getLink('New Activity').click()
    >>> stephan.getControl('Title').value = 'HW 3'
    >>> stephan.getControl('Description').value = 'Homework 3'
    >>> stephan.getControl('Category').value = ['assignment']
    >>> stephan.getControl(
    ...     name='field.scoresystem.existing').value = ['100 Points']
    >>> stephan.getControl('Add').click()
    >>> 'HW 3' in stephan.contents
    True

    >>> stephan.getControl(name='delete:list').value = ['Activity-4']
    >>> stephan.getControl('Delete').click()
    >>> 'HW 3' in stephan.contents
    False


Grading
-------

Now that we have both, students and activities, we can enter the gradebook.

    >>> stephan.getLink('SchoolTool').click()
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

But since I entered an invlaid value for Homework 2, we get an error message:

    >>> 'The grade 56 for activity HW 2 is not valid.' in stephan.contents
    True

Also note that all the other entered values should be retained:

    >>> 'value="93"' in stephan.contents
    True
    >>> 'value="87"' in stephan.contents
    True
    >>> 'value="56"' in stephan.contents
    True

    >>> stephan.getControl('HW 2').value = u'36'
    >>> stephan.getControl('Update').click()

The screen will return to the grade overview, where the grades are no visible:

    >>> '>93<' in stephan.contents
    True
    >>> '>87<' in stephan.contents
    True
    >>> '>36<' in stephan.contents
    True

Now let's enter again and change a grade:

    >>> stephan.getLink('Claudia Richter').click()
    >>> stephan.getControl('HW 2').value = u'46'
    >>> stephan.getControl('Update').click()

    >>> '>46<' in stephan.contents
    True

When you want to delete an evaluation altogether, simply blank the value:

    >>> stephan.getLink('Claudia Richter').click()
    >>> stephan.getControl('HW 2').value = u''
    >>> stephan.getControl('Update').click()

    >>> '>46<' in stephan.contents
    False

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

    >>> stephan.getControl('Paul Cardune').value = u'190'
    >>> stephan.getControl('Tom Hoffman').value = u'82'

    >>> stephan.getControl('Update').click()

Again, we entered an invalid value, this time for Paul:

    >>> 'The grade 190 for Paul Cardune is not valid.' in stephan.contents
    True

Also note that all the other entered values should be retained:

    >>> 'value="190"' in stephan.contents
    True
    >>> 'value="82"' in stephan.contents
    True
    >>> 'value="87"' in stephan.contents
    True

    >>> stephan.getControl('Paul Cardune').value = u'90'
    >>> stephan.getControl('Update').click()

The screen will return to the grade overview, where the grades are now
visible:

    >>> '>90<' in stephan.contents
    True
    >>> '>82<' in stephan.contents
    True
    >>> '>87<' in stephan.contents
    True

Now let's enter again and change a grade:

    >>> stephan.getLink('HW 1').click()
    >>> stephan.getControl('Claudia Richter').value = u'98'
    >>> stephan.getControl('Update').click()

    >>> '>98<' in stephan.contents
    True

When you want to delete an evaluation altogether, simply blank the value:

    >>> stephan.getLink('HW 1').click()
    >>> stephan.getControl('Claudia Richter').value = u''
    >>> stephan.getControl('Update').click()

    >>> '>98<' in stephan.contents
    False

Of course, you can also abort the grading.

    >>> stephan.getLink('HW 1').click()
    >>> stephan.getControl('Cancel').click()
    >>> stephan.url
    'http://localhost/sections/phyi1/gradebook/index.html'


Entering Scores for a Cell (Student, Activity)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When you click directly on the grade, you can also edit it. Let's day that we
want to modify Claudia's Homework 2 grade. Until now she had a 76:

    >>> stephan.getLink('90').click()

The screen that opens gives you several pieces of information, such as the
student's name,

    >>> 'Paul Cardune' in stephan.contents
    True

the activity name,

    >>> 'HW 1' in stephan.contents
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
    '90'
    >>> stephan.getControl('Delete').click()
    >>> stephan.getControl('Grade').value
    ''

Now let's enter a new grade:

    >>> stephan.getControl('Grade').value = '86'
    >>> stephan.getControl('Update').click()

    >>> stephan.url
    'http://localhost/sections/phyi1/gradebook/index.html'
    >>> '>86<' in stephan.contents
    True

Of course, you can also cancel actions:

    >>> stephan.getLink('86').click()
    >>> stephan.getControl('Grade').value = '66'
    >>> stephan.getControl('Cancel').click()

    >>> stephan.url
    'http://localhost/sections/phyi1/gradebook/index.html'
    >>> '>86<' in stephan.contents
    True


Statistics
~~~~~~~~~~

On the bottom of the gradebook, there are several statistical values for each
activity. Let's clear all Homework 1 grades to see the effects:

    >>> stephan.getLink('HW 1').click()
    >>> stephan.getControl('Claudia Richter').value = u''
    >>> stephan.getControl('Paul Cardune').value = u''
    >>> stephan.getControl('Tom Hoffman').value = u''
    >>> stephan.getControl('Update').click()

If there are no grades, all statistical values should not be available:

    >>> print stephan.contents
    <BLANKLINE>
    ...
    <tr class="Statistic">
      <td class="name">Average</td>
      <td class="value">N/A</td>
      ...
    </tr>
    <tr class="Statistic">
      <td class="name">Percent Average</td>
      <td class="value">N/A</td>
      ...
    </tr>
    <tr class="Statistic">
      <td class="name">Median</td>
      <td class="value">N/A</td>
      ...
    </tr>
    <tr class="Statistic">
      <td class="name">Standard Deviation</td>
      <td class="value">N/A</td>
      ...
    </tr>
    <tr class="Statistic">
      <td class="name">Variance</td>
      <td class="value">N/A</td>
      ...
    </tr>
    ...

If I add a grade for Claudia, then the first statistics should show. Note that
the standard deviation and variance cannot be computed, since there are no
degrees of freedom.

    >>> stephan.getLink('HW 1').click()
    >>> stephan.getControl('Claudia Richter').value = u'80'
    >>> stephan.getControl('Update').click()

    >>> print stephan.contents
    <BLANKLINE>
    ...
    <tr class="Statistic">
      <td class="name">Average</td>
      <td class="value">80.0</td>
      ...
    </tr>
    <tr class="Statistic">
      <td class="name">Percent Average</td>
      <td class="value">80.0</td>
      ...
    </tr>
    <tr class="Statistic">
      <td class="name">Median</td>
      <td class="value">80.0</td>
      ...
    </tr>
    <tr class="Statistic">
      <td class="name">Standard Deviation</td>
      <td class="value">N/A</td>
      ...
    </tr>
    <tr class="Statistic">
      <td class="name">Variance</td>
      <td class="value">N/A</td>
      ...
    </tr>
    ...

Once more than one grade is entered, all statistics show:

    >>> stephan.getLink('HW 1').click()
    >>> stephan.getControl('Paul Cardune').value = u'70'
    >>> stephan.getControl('Tom Hoffman').value = u'90'
    >>> stephan.getControl('Update').click()

    >>> print stephan.contents
    <BLANKLINE>
    ...
    <tr class="Statistic">
      <td class="name">Average</td>
      <td class="value">80.0</td>
      ...
    </tr>
    <tr class="Statistic">
      <td class="name">Percent Average</td>
      <td class="value">80.0</td>
      ...
    </tr>
    <tr class="Statistic">
      <td class="name">Median</td>
      <td class="value">80.0</td>
      ...
    </tr>
    <tr class="Statistic">
      <td class="name">Standard Deviation</td>
      <td class="value">10.0</td>
      ...
    </tr>
    <tr class="Statistic">
      <td class="name">Variance</td>
      <td class="value">100.0</td>
      ...
    </tr>
    ...


Sorting
~~~~~~~

Another feature of the gradebook is the ability to sort each column in a
descending and ascending fashion. By default the student's name is sorted
alphabetically:

    >>> stephan.contents.find('Claudia') \
    ...     < stephan.contents.find('Paul') \
    ...     < stephan.contents.find('Tom')
    True

Once I click on the name sort button (again), the order is reversed:

    >>> stephan.getLink(url='sort_by=student').click()
    >>> stephan.contents.find('Claudia') \
    ...     > stephan.contents.find('Paul') \
    ...     > stephan.contents.find('Tom')
    True

Then we want to sort by grade in Homework 1, so we should have:

    >>> import re
    >>> url = re.compile('.*sort_by=-?[0-9]+')
    >>> stephan.getLink(url=url).click()
    >>> stephan.contents.find('Paul') \
    ...     < stephan.contents.find('Claudia') \
    ...     < stephan.contents.find('Tom')
    True

Clicking it again, reverses the order:

    >>> stephan.getLink(url=url).click()
    >>> stephan.contents.find('Paul') \
    ...     > stephan.contents.find('Claudia') \
    ...     > stephan.contents.find('Tom')
    True
