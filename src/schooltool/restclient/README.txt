SchoolTool REST API client
==========================


Big Fat Warning
---------------

This is currently science fiction, i.e. it doesn't work.  It represents an idea
of the ideal restive client API.

Perhaps it will be possible to convert it to a working functional test.


Introduction
------------

Let us connect to the SchoolTool server running on localhost, port 7001:

    >>> from schooltool.restclient.restclient import SchoolToolClient
    >>> client = SchoolToolClient('localhost', port=7001, ssl=False)

Since we do not want to make actual HTTP connections in a functional test, we'll
use a stub connectionFactory.

    >>> from schooltool.restclient.tests import RestConnectionFactory
    >>> client.connectionFactory = RestConnectionFactory

We will authenticate as the user 'manager' with password 'schooltool'

    >>> client.setUser('manager', 'schooltool')

We can take a look around

    >>> print client.get('/')
    <schooltool xmlns:xlink="http://www.w3.org/1999/xlink">
      <message>Welcome to the SchoolTool server</message>
      <containers>
        <container xlink:type="simple"
                   xlink:href="http://localhost:7001/terms"
                   xlink:title="terms"/>
        <container xlink:type="simple"
                   xlink:href="http://localhost:7001/persons"
                   xlink:title="persons"/>
        <container xlink:type="simple"
                   xlink:href="http://localhost:7001/courses"
                   xlink:title="courses"/>
        <container xlink:type="simple"
                   xlink:href="http://localhost:7001/levels"
                   xlink:title="levels"/>
        <container xlink:type="simple"
                   xlink:href="http://localhost:7001/groups"
                   xlink:title="groups"/>
        <container xlink:type="simple"
                   xlink:href="http://localhost:7001/ttschemas"
                   xlink:title="ttschemas"/>
        <container xlink:type="simple"
                   xlink:href="http://localhost:7001/sections"
                   xlink:title="sections"/>
        <container xlink:type="simple"
                   xlink:href="http://localhost:7001/resources"
                   xlink:title="resources"/>
      </containers>
    </schooltool>


XXX mg: idea: RESTiveClient() that has get/put/post/delete, and
        SchoolToolClient which either subclasses or delegates and provides
        high-level API.
    ignas: +5


High-level API
--------------

But working at this low level is not convenient.  SchoolTool client provides
high-level access methods.

Here's how you can look at the person list:

    >>> all_persons = client.getPersons()
    >>> all_persons
    [<PersonRef SchoolTool Manager at http://localhost:7001/persons/manager>]

Initially our server has only one user -- the manager

    >>> manager = all_persons[0]
    >>> manager.title
    u'SchoolTool Manager'
    >>> manager.url
    u'http://localhost:7001/persons/manager'

Here's how you can look at the group list:

    >>> all_groups = client.getGroups()
    >>> all_groups
    [<GroupRef Manager at http://localhost:7001/groups/manager>]

    >>> manager_group = all_groups[0]
    >>> manager_group.title
    u'Manager'
    >>> manager_group.url
    u'http://localhost:7001/groups/manager'

You can take a closer look at that person or group

    >>> person_info = manager.getInfo()
    >>> person_info.title
    u'SchoolTool Manager'

    >>> group_info = manager_group.getInfo()
    >>> group_info.title
    u'Manager'
    >>> group_info.description
    u'The manager group.'

    >>> manager_group.getMembers()
    []

Initially there are no resources, courses nor sections:

    >>> client.getResources()
    []

    >>> client.getCourses()
    []

    >>> client.getSections()
    []


Importing users
---------------

Suppose we need to import a list of users.  Some of the users have photos

    >>> data = '''
    ... Person1, username1, password1
    ... Person5, username5, password5, snukis.jpg
    ... '''.strip()

    >>> import os
    >>> import schooltool.restclient.tests
    >>> basedir = os.path.dirname(schooltool.restclient.tests.__file__)

    >>> import csv
    >>> for row in csv.reader(data.splitlines()):
    ...     title, username, password = map(str.strip, row[:3])
    ...     person = client.createPerson(title, username)
    ...     person.setPassword(password)
    ...     if len(row) > 3:
    ...         filename = os.path.join(basedir, row[3].strip())
    ...         photo = file(filename, 'rb').read()
    ...         person.setPhoto(photo, 'image/jpeg')

XXX TODO: getPhoto -- how do we get the content type?  What happens when there
is no photo -- do we get None or an exception?


Importing groups
----------------

Suppose we need to import a list of groups and persons, creating them on
demand, or using existing ones, if they are already there.

    >>> data = '''
    ... Group1 Person1
    ... Group1 Person2
    ... Group2 Person1
    ... '''.strip()

We will need to know which groups and persons we have already created.

    >>> group_map = {}
    >>> person_map = {}

First let us populate the maps with existing users and groups:

    >>> for group in client.getGroups():
    ...     group_map[group.title] = group

    >>> for person in client.getPersons():
    ...     person_map[person.title] = person

Now we loop through the data line by line, creating persons and groups if
necessary, and adding persons as group members.

    >>> from schooltool.restclient.restclient import SchoolToolError
    >>> for line in data.splitlines():
    ...     group_title, person_title = line.split()
    ...     group = group_map.get(group_title)
    ...     if group is None:
    ...         group = client.createGroup(group_title)
    ...         group_map[group_title] = group
    ...     person = person_map.get(person_title)
    ...     if person is None:
    ...         username = person_title.lower().replace(' ', '-')
    ...         person = client.createPerson(person_title, username)
    ...         person_map[person_title] = person
    ...     try:
    ...         group.addMember(person)
    ...     except SchoolToolError, e:
    ...         pass # already a member

XXX mg: but if we get 500 ServerError, or http timeout/connection refused, then
we don't want to ignore that exception!


More imports
------------

We can add Resources, Sections, Courses in a similar way too:

Resources:

    >>> data = '''
    ... Resource1, A simple resource
    ... Resource2, A complex resource
    ... beamer-1, A good new beamer
    ... beamer-2, An old bad beamer
    ... '''.strip()

    >>> for row in csv.reader(data.splitlines()):
    ...     title, description = map(str.strip, row)
    ...     resource = client.createResource(title, description)

Courses:

    >>> data = '''
    ... History, History for the sixth grade
    ... English, English for the first grade
    ... '''.strip()

    >>> for row in csv.reader(data.splitlines()):
    ...     title, description = map(str.strip, row)
    ...     course = client.createCourse(title, description)

Sections are a bit more difficult because most of the time they come
attached to some course, have some learners and an instructor:

    >>> data = '''
    ... History, 6a, Hoffman
    ... English, 6a, James
    ... History, 7a, Nathaniel
    ... '''.strip()

We will need to know which groups and courses we have already created.

    >>> person_map = {}
    >>> group_map = {}
    >>> course_map = {}

First let us populate the maps with existing groups and courses:

    >>> for person in client.getPersons():
    ...     person_map[person.title] = person

    >>> for group in client.getGroups():
    ...     group_map[group.title] = group

    >>> for course in client.getCourses():
    ...     course_map[course.title] = course

Now we loop through the data line by line, creating courses and groups if
necessary, and adding sections as group members.

    >>> for line in data.splitlines():
    ...     course_title, group_title, person_title = line.split()
    ...     group = group_map.get(group_title)
    ...     if group is None:
    ...         group = client.createGroup(group_title)
    ...         group_map[group_title] = group
    ...     course = course_map.get(course_title)
    ...     if course is None:
    ...         course = client.createCourse(course_title)
    ...         course_map[course_title] = course
    ...     person = person_map.get(person_title)
    ...     if person is None:
    ...         username = person_title.lower().replace(' ', '-')
    ...         person = client.createPerson(person_title, username)
    ...         person_map[person_title] = person
    ...     section = client.createSection('%s %s' % (course_title, group_title))
    ...     try:
    ...         course.addSection(section)
    ...         section.addInstructor(person)
    ...         section.addLearner/Member(group)
    ...     except SchoolToolError, e:
    ...         pass # already a member


Timetabling
-----------

At the moment we can at least list existing terms:

    >>> client.getTerms()
    [<TermRef 2004 Fall at http://localhost:7001/terms/2004-fall>]

Same for school timetables:

    >>> client.getSchoolTimetabes()
    [<SchoolTimetableRef Standard Weekly at http://localhost:7001/ttschemas/standard-weekly>]


Information
-----------

Use case: download all information about a resource, edit it, upload it back.

    >>> resource = client.getResource('/resources/beamer-2')
    >>> resource.title
    >>> resource.url
    >>> resource_info = resource.getInfo()
    >>> resource_info.title
    '...'
    >>> resource_info.description
    '...'
    >>> resource_info.is_location
    False

Modify!

    >>> resource_info.is_location = True
    >>> resource_info.description += '\n' + 'Tastes good with mustard.'
    >>> resource.changeInfo(resource_info)

You do it the same way with persons/groups/courses/sections.


Deleting objects
----------------

Suppose we got bored of the second beamer.

    >>> resource.delete()

or we could do

    >>> client.delete('/resources/beamer-2')

That's it.


Calendars
---------

    >>> manager.calendar
    <CalendarRef http://localhost:7001/persons/manager/calendar>
    >>> manager.calendar.get_iCalendar()
    'BEGIN:VCALENDAR...'


Arbitrary relationships
-----------------------

You can create new relationships

    >>> manager.createRelationship(beamer.calendar,
    ...                            URICalendarSubscription,
    ...                            URICalendarProvider)

You can see a list of all relationships.

    >>> relationships = manager.getRelationships()
    >>> relationships
    [<Relationship /persons/manager (Member) -> /groups/manager (Group)>,
     <Relationship /perosns/manbager (Member) -> /resources/beamer-1 (Resource)>]

    >>> relationships[0].url
    'http://localhost/persons/manager/relationships/1'
    >>> relationships[0].target
    <ObjectRef DaGroup#2 http:///localhost:7001/...>
    >>> relationships[0].target.url
    'http://loclahost:8001/resources/beamer-1'
    >>> relationships[0].target.title
    'Da group # 2'
    >>> relationships[0].target_role
    URIGroup
    >>> relationships[0].arcrole
    URIMememberthisp

You can destroy existing ones

    >>> relationships[-1].delete()

Ta-da.
