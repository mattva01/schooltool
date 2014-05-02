===================================
SchoolTool Selenium Testing Support
===================================

Browser extensions
==================

We can access Selenium browser extensions using the 'ui' attribute of
the browser object, like this:

    >>> browser.ui.EXTENSION_GOES_HERE

Most of the extensions are coded in the stesting.py modules in their
corresponding packages. Look for their functional tests in the
selenium_extensions.txt stest files.

We have browser extensions for:

Logging in
----------

* browser.ui.login()

  Required parameters:
    username
    password

Adding persons
--------------

* browser.ui.person.add()

  Required parameters:
    first_name
    last_name
    username
    password
  Optional keyword parameters:
    prefix
    middle_name
    suffix
    preferred_name
    gender: text of the option to select
    birth_date: YYYY-MM-DD date
    ID
    ethnicity: text of the option to select
    language
    placeofbirth
    citizenship
    group: text of the option to select
    advisor: text of the option to select

  NOTE: if ends is not set, the section will end in the starting term

Adding advisors for a person
----------------------------

* browser.ui.person.advisors.add()

  Required parameters:
    username
    advisors: list with person usernames

    NOTE: it doesn't matter if some of the usernames are already
          advisors of the person

Adding advisees for a person
----------------------------

* browser.ui.person.advisees.add()

  Required parameters:
    username
    advisees: list with person usernames

    NOTE: it doesn't matter if some of the usernames are already
          advisees of the person

Adding school years
------------------

* browser.ui.schoolyear.add()

  Required parameters:
    title
    first: YYYY-MM-DD date
    last: YYYY-MM-DD date
  Optional keyword parameters:
    copy_groups: list of non built-in group identifiers from previous year
    copy_members: list of non built-in group identifiers from previous year
    copy_courses: bool
    copy_timetables: bool

Adding terms
------------

* browser.ui.term.add()

  Required parameters:
    schoolyear: title of the school year
    title
    first: YYYY-MM-DD date
    last: YYYY-MM-DD date
  Optional keyword parameters:
    holidays: list of YYYY-MM-DD dates
    weekends: list of day weeks (Monday, ..., Sunday)

Adding courses
--------------

* browser.ui.course.add()

  Required parameters:
    schoolyear: title of the school year
    title
  Optional keyword parameters:
    description
    course_id
    government_id
    credits
    level: title of the level

Adding sections
---------------

* browser.ui.section.add()

  Required parameters:
    schoolyear: title of the school year
    term: title of the term
    course: title of the course
  Optional keyword parameters:
    title
    description
    ends: title of the term when it ends
    instructors: list with person usernames
    instructors_state: title of the state
    instructors_date: YYYY-MM-DD date
    students: list with person usernames
    students_state: title of the state
    students_date: YYYY-MM-DD date

  NOTE: if ends is not set, the section will end in the starting term

Visiting a section
------------------

* browser.ui.section.go()

  Required parameters:
    schoolyear: title of the school year
    term: title of the term
    section: title of the section

Adding instructors to a section
-------------------------------

* browser.ui.section.instructors.add()

  Required parameters:
    schoolyear: title of the school year
    term: title of the term
    section: title of the section
    instructors: list with person usernames
  Optional keyword parameters:
    state: title of the state
    date: YYYY-MM-DD date

    NOTE: it doesn't matter if some of the usernames are already
          instructors of the section

Removing instructors from a section
-----------------------------------

With the new temporal relationship implementation, remove really
becomes an updating action.

* browser.ui.section.instructors.remove()

  Required parameters:
    schoolyear: title of the school year
    term: title of the term
    section: title of the section
    instructors: list with person usernames
  Optional keyword parameters:
    state: title of the state
    date: YYYY-MM-DD date

Adding students to a section
----------------------------

* browser.ui.section.students.add()

  Required parameters:
    schoolyear: title of the school year
    term: title of the term
    section: title of the section
    students: list with person usernames
  Optional keyword parameters:
    state: title of the state
    date: YYYY-MM-DD date

    NOTE: it doesn't matter if some of the usernames are already
          students of the section

Removing students from a section
--------------------------------

With the new temporal relationship implementation, remove really
becomes an updating action.

* browser.ui.section.students.remove()

  Required parameters:
    schoolyear: title of the school year
    term: title of the term
    section: title of the section
    students: list with person usernames
  Optional keyword parameters:
    state: title of the state
    date: YYYY-MM-DD date

Adding groups
-------------

* browser.ui.group.add()

  Required parameters:
    schoolyear: title of the school year
    title
  Optional keyword parameters:
    description

Visiting a group
----------------

* browser.ui.group.go()

  Required parameters:
    schoolyear: title of the school year
    group: title of the group

Adding members to a group
-------------------------

* browser.ui.group.members.add()

  Required parameters:
    schoolyear: title of the school year
    group: title of the group
    members: list with person usernames
  Optional keyword parameters:
    state: title of the state
    date: YYYY-MM-DD date

    NOTE: it doesn't matter if some of the usernames are already
          members of the group

Removing members from a group
-----------------------------

* browser.ui.group.members.remove()

With the new temporal relationship implementation, remove really
becomes an updating action.

  Required parameters:
    schoolyear: title of the school year
    group: title of the group
    members: list with person usernames
  Optional keyword parameters:
    state: title of the state
    date: YYYY-MM-DD date

Element extensions
==================

We can access Selenium element extensions using the 'ui' attribute of
the element object, like this:

    >>> element = browser.QUERY_THE_ELEMENT_SOMEHOW
    >>> element.ui.EXTENSION_GOES_HERE

The element extensions are coded in the stesting.py module of the
skin.flourish package.

We have element extensions for:

Entering dates
--------------

* element.ui.enter_date()

  Required parameters:
    date: YYYY-MM-DD date

Selecting an option in a menu
-----------------------------

* element.ui.select_option()

  Required parameters:
    option: text of the option to select

Setting the value of a field without caring about its type
----------------------------------------------------------

* element.ui.set_value

  Required parameters:

    value: text that can represent a regular text input, the content
    of a textarea (it's possible to set break lines using \n), a
    YYYY-MM-DD used in the datepicker widget or the text of an option
    in a menu


=============================================
SchoolTool Gradebook Selenium Testing Support
=============================================

Browser extensions
==================

These extensions are coded in the stesting.py module of the
schooltool.app package and they're tested in the
selenium_extesions.txt file of the schooltool.gradebook package and
the selenium_extension.txt file of the schooltool.lyceum.journal
package.

We have browser extensions for:

Printing a worksheet
--------------------

* browser.ui.gradebook.worksheet.pprint()

  Optional keyword parameters:
    show_validation: bool

  NOTE: the current url must be the worksheet's url

  NOTE: if show_validation is set, a code will be printed next to the
  input field. The codes meaning are:

    * v: valid score
    * e: extra credit score
    * i: invalid score

Scoring an activity for a student
---------------------------------

* browser.ui.gradebook.worksheet.score()

  Required parameters:
    student: title of the student row
    activity: label of the column
    grade

  NOTE: the current url must be the worksheet's url
