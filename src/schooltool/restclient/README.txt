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

    >>> from schooltool.restclient import SchoolToolClient
    >>> client = SchoolToolClient('localhost', port=7001, ssl=False)

We will authenticate as the user 'manager' with password 'schooltool'

    >>> client.setUser('manager', 'schooltool')

We can take a look around

    >>> print client.get('/')
    <schooltool>
      Welcome, come see a bit of XML here.
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
    [<Person SchoolTool Manager at http://localhost:7001/persons/manager>]

Initially our server has only one user -- the manager

    >>> manager = all_persons[0]
    >>> manager.title
    u'SchoolTool Manager'
    >>> manager.url
    u'http://localhost:7001/persons/manager'

Here's how you can look at the group list:

    >>> all_groups = client.getGroups()
    >>> all_groups
    [<Group Manager at http://localhost:7001/groups/manager>]

    >>> manager_group = all_groups[0]
    >>> manager_group.title
    u'Manager'
    >>> manager_group.url
    u'http://localhost:7001/groups/manager'
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

    >>> import csv
    >>> for row in csv.reader(data.splitlines()):
    ...     title, username, password = row[:3]
    ...     person = client.createPerson(title, username)
    ...     person.setPassword(password)
    ...     if len(row) > 3:
    ...         photo = file(row[3], 'rb').read()
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

