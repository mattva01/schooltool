=============
The Gradebook
=============

There are many tasks that are involved in setting up and using a
gradebook. The first task the administrator has to complete during the
SchoolTool setup is the configuration of the categories. So let's log in as a
manager:

   >>> from schooltool.app.browser.ftests import setup
   >>> manager = setup.logInManager()


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

This completes the initial school setup.


Term Setup
----------

Every term, the administrators of a school are going to setup sections. So
let's add a section for our course:

    >>> from schooltool.app.browser.ftests import setup
    >>> setup.addSection('Physics I')

But what would a section be without some students and a teacher?

    >>> from schooltool.app.browser.ftests.setup import addPerson
    >>> addPerson('Paul Cardune', 'paul', 'pwd', groups=['students'])
    >>> addPerson('Tom Hoffman', 'tom', 'pwd', groups=['students'])
    >>> addPerson('Claudia Richter', 'claudia', 'pwd', groups=['students'])
    >>> addPerson('Stephan Richter', 'stephan', 'pwd', groups=['teachers'])

Now we can add those people to the section:

    >>> manager.getLink('Courses').click()
    >>> manager.getLink('Physics I').click()
    >>> manager.getLink('(1)').click()

    >>> manager.getLink('edit individuals').click()
    >>> manager.getControl('Paul Cardune').click()
    >>> manager.getControl('Tom Hoffman').click()
    >>> manager.getControl('Claudia Richter').click()
    >>> manager.getControl('Add').click()
    >>> manager.getControl('OK').click()

    >>> 'Paul Cardune' in manager.contents
    True

    >>> manager.getLink('edit instructors').click()
    >>> manager.getControl('Stephan Richter').click()
    >>> manager.getControl('Add').click()
    >>> manager.getControl('OK').click()


Instructor should be automatically capable of manipulating activities
and other section data.

Gradebook Management
--------------------

Once the term started, the instructor of the section will start by
creating two worksheets, one for each week in our two week section.

    >>> stephan = setup.logIn('stephan', 'pwd')

    >>> stephan.getLink('SchoolTool').click()
    >>> stephan.getLink('Courses').click()
    >>> stephan.getLink('Physics I').click()
    >>> stephan.getLink('(1)').click()
    >>> stephan.getLink('Activities').click()

    >>> stephan.getLink('New Worksheet').click()
    >>> stephan.getControl('Title').value = 'Week 1'
    >>> stephan.getControl('Add').click()
    >>> 'Week 1' in stephan.contents
    True

    >>> stephan.getLink('New Worksheet').click()
    >>> stephan.getControl('Title').value = 'Week 2'
    >>> stephan.getControl('Add').click()
    >>> 'Week 2' in stephan.contents
    True

Note that 'Week 1' is the currently selected worksheet.

    >>> '<option value="Week 1" selected="selected">Week 1</option>' in \
    ...  stephan.contents
    True

Now, let's add some activities to it.

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
    >>> stephan.getControl('Title').value = 'Quiz'
    >>> stephan.getControl('Description').value = 'Week 1 Pop Quiz'
    >>> stephan.getControl('Category').value = ['exam']
    >>> stephan.getControl(
    ...     name='field.scoresystem.existing').value = ['100 Points']
    >>> stephan.getControl('Add').click()
    >>> 'Quiz' in stephan.contents
    True

But, oh, we really did not want to make Homework 1 out of a hundred points,
but only out of 50. So let's edit it:

    >>> stephan.getLink('HW 1').click()
    >>> stephan.getControl('Custom score system').click()
    >>> stephan.getControl('Maximum').value = '50'
    >>> stephan.getControl('Apply').click()

Now let's change the current workskeet to 'Week 2'.

    >>> stephan.open(stephan.url+'?form-submitted=&currentWorksheet=Week%202')
    >>> '<option value="Week 2" selected="selected">Week 2</option>' in \
    ...  stephan.contents
    True

Now we'll add some activities to it.

    >>> stephan.getLink('New Activity').click()
    >>> stephan.getControl('Title').value = 'HW 2'
    >>> stephan.getControl('Description').value = 'Homework 2'
    >>> stephan.getControl('Category').value = ['assignment']
    >>> stephan.getControl(
    ...     name='field.scoresystem.existing').value = ['100 Points']
    >>> stephan.getControl('Add').click()
    >>> 'HW 2' in stephan.contents
    True

    >>> stephan.getLink('New Activity').click()
    >>> stephan.getControl('Title').value = 'Final'
    >>> stephan.getControl('Description').value = 'Final Exam'
    >>> stephan.getControl('Category').value = ['exam']
    >>> stephan.getControl(
    ...     name='field.scoresystem.existing').value = ['100 Points']
    >>> stephan.getControl('Add').click()
    >>> 'Final' in stephan.contents
    True

Now that we have all our activities setup, we would like to rearrange their
order more logically. The final in week 2 should really be at the end of the
list. In the browser you should usually just select the new position and some
Javascript would submit the form. Since Javascript is not working in the
tests, we submit, the form manually:

    >>> stephan.open(stephan.url+'?form-submitted=&pos.Activity-3=3')
    >>> stephan.contents.find('HW 2') \
    ...     < stephan.contents.find('Final')
    True

You can also delete activities that you have created:

    >>> stephan.getLink('New Activity').click()
    >>> stephan.getControl('Title').value = 'HW 3'
    >>> stephan.getControl('Description').value = 'Homework 3'
    >>> stephan.getControl('Category').value = ['assignment']
    >>> stephan.getControl(
    ...     name='field.scoresystem.existing').value = ['100 Points']
    >>> stephan.getControl('Add').click()
    >>> 'HW 3' in stephan.contents
    True

    >>> stephan.getControl(name='delete:list').value = ['Activity-3']
    >>> stephan.getControl('Delete').click()
    >>> 'HW 3' in stephan.contents
    False

Fianlly, let's change the current workskeet back to 'Week 1'.  This setting
of current worksheet will be in effect for the gradebook as well.

    >>> stephan.open(stephan.url+'?form-submitted=&currentWorksheet=Week%201')
    >>> '<option value="Week 1" selected="selected">Week 1</option>' in \
    ...  stephan.contents
    True


Grading
-------

Now that we have both, students and activities, we can enter the gradebook.

    >>> stephan.getLink('SchoolTool').click()
    >>> stephan.getLink('Courses').click()
    >>> stephan.getLink('Physics I').click()
    >>> stephan.getLink('(1)').click()
    >>> stephan.getLink('Gradebook').click()

The initial gradebook screen is a simple spreadsheet. In order to prevent
accidental score submission, we do not allow to enter grades in this
table. Instead you select a row (student), column (activity) or cell (student,
activity) to enter the scores.

Since we just loaded up the gradebook for the first time, the current worksheet
will be the first one, Week 1.  Only the activities for that worksheet should
appear.

    >>> 'HW 1' in stephan.contents and 'Quiz' in stephan.contents
    True
    >>> 'HW 2' in stephan.contents or 'Final' in stephan.contents
    False



Entering Scores for a Row (Student)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Let's say we want to enter the grades for Claudia. All we do is to simply
click on her name:

    >>> stephan.getLink('Claudia Richter').click()

Now we just enter the grades:

    >>> stephan.getControl('HW 1').value = u'-1'
    >>> stephan.getControl('Quiz').value = u'56'
    >>> stephan.getControl('Update').click()

But since I entered an invlaid value for Homework 1, we get an error message:

    >>> 'The grade -1 for activity HW 1 is not valid.' in stephan.contents
    True

Also note that all the other entered values should be retained:

    >>> 'value="-1"' in stephan.contents
    True
    >>> 'value="56"' in stephan.contents
    True
    >>> stephan.getControl('HW 1').value = u'36'
    >>> stephan.getControl('Update').click()

The screen will return to the grade overview, where the grades are no visible:

    >>> '>36<' in stephan.contents
    True
    >>> '>56<' in stephan.contents
    True

Also, there will be an average grade displayed that the teacher can use to 
formulate a final grade.

    >>> '>61%<' in stephan.contents
    True

Now let's enter again and change a grade:

    >>> stephan.getLink('Claudia Richter').click()
    >>> stephan.getControl('HW 1').value = u'46'
    >>> stephan.getControl('Update').click()
    >>> '>46<' in stephan.contents
    True

When you want to delete an evaluation altogether, simply blank the value:

    >>> stephan.getLink('Claudia Richter').click()
    >>> stephan.getControl('HW 1').value = u''
    >>> stephan.getControl('Update').click()
    >>> '>46<' in stephan.contents
    False

Of course, you can also abort the grading.

    >>> stephan.getLink('Claudia Richter').click()
    >>> stephan.getControl('Cancel').click()
    >>> stephan.url
    'http://localhost/sections/1/gradebook/index.html'

Let's put Claudia's grade back in:

    >>> stephan.getLink('Claudia Richter').click()
    >>> stephan.getControl('HW 1').value = u'36'
    >>> stephan.getControl('Update').click()
    >>> '>36<' in stephan.contents
    True


Entering Scores for a Column (Activity)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Let's say we want to enter the grades for Homework 1. All we do is to simply
click on the activity's name:

    >>> stephan.getLink('HW 1').click()

Now we just enter the grades. Since Claudia has already a grade, we only need
to grade Paul and Tom:

    >>> stephan.getControl('Paul Cardune').value = u'-1'
    >>> stephan.getControl('Tom Hoffman').value = u'42'
    >>> stephan.getControl('Update').click()

Again, we entered an invalid value, this time for Paul:

    >>> 'The grade -1 for Paul Cardune is not valid.' in stephan.contents
    True

Also note that all the other entered values should be retained:

    >>> 'value="-1"' in stephan.contents
    True
    >>> 'value="42"' in stephan.contents
    True
    >>> 'value="36"' in stephan.contents
    True
    >>> stephan.getControl('Paul Cardune').value = u'40'
    >>> stephan.getControl('Update').click()

The screen will return to the grade overview, where the grades are now
visible:

    >>> '>40<' in stephan.contents
    True
    >>> '>42<' in stephan.contents
    True
    >>> '>36<' in stephan.contents
    True

Now let's enter again and change a grade:

    >>> stephan.getLink('HW 1').click()
    >>> stephan.getControl('Claudia Richter').value = u'48'
    >>> stephan.getControl('Update').click()
    >>> '>48<' in stephan.contents
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
    'http://localhost/sections/1/gradebook/index.html'


Entering Scores for a Cell (Student, Activity)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When you click directly on the grade, you can also edit it. Let's day that we
want to modify Claudia's Quiz grade. Until now she had a 56:

    >>> stephan.getLink('56').click()

The screen that opens gives you several pieces of information, such as the
student's name,

    >>> 'Claudia Richter' in stephan.contents
    True

the activity name,

    >>> 'Quiz' in stephan.contents
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
    '56'
    >>> stephan.getControl('Delete').click()
    >>> stephan.getControl('Grade').value
    ''

Now let's enter a new grade:

    >>> stephan.getControl('Grade').value = '86'
    >>> stephan.getControl('Update').click()
    >>> stephan.url
    'http://localhost/sections/1/gradebook/index.html'
    >>> '>86<' in stephan.contents
    True

Of course, you can also cancel actions:

    >>> stephan.getLink('86').click()
    >>> stephan.getControl('Grade').value = '66'
    >>> stephan.getControl('Cancel').click()
    >>> stephan.url
    'http://localhost/sections/1/gradebook/index.html'
    >>> '>86<' in stephan.contents
    True


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
    ...     < stephan.contents.find('Tom') \
    ...     < stephan.contents.find('Claudia')
    True

Clicking it again, reverses the order:

    >>> stephan.getLink(url=url).click()
    >>> stephan.contents.find('Claudia') \
    ...     < stephan.contents.find('Tom') \
    ...     < stephan.contents.find('Paul')
    True


My Grades
---------

Students should also be able to view their grades (not change them), so there's
a view for the student to see them.  Let's log in as Claudia and go to her grades
for the section.  It will come up with Week 1 as the current worksheet,

    >>> claudia = setup.logIn('claudia', 'pwd')
    >>> claudia.open('http://localhost/sections/1/mygrades')
    >>> 'HW 1' in claudia.contents and 'Quiz' in claudia.contents
    True
    >>> 'HW 2' in claudia.contents or 'Final' in claudia.contents
    False
    >>> claudia.contents.find('Current Grade: 86%') \
    ...     < claudia.contents.find('HW 1') \
    ...     < claudia.contents.find('Quiz') \
    ...     < claudia.contents.find('86/100')
    True

