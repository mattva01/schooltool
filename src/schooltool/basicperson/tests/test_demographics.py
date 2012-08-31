#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2008 Shuttleworth Foundation
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
Tests for person demographics
"""
import unittest
import doctest

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.basicperson.person import BasicPerson
from schooltool.basicperson.interfaces import IDemographics
from schooltool.basicperson.interfaces import IDemographicsFields
from schooltool.basicperson.demographics import DateFieldDescription
from schooltool.basicperson.demographics import EnumFieldDescription
from schooltool.basicperson.demographics import IntFieldDescription
from schooltool.basicperson.demographics import setUpDefaultDemographics
from schooltool.basicperson.demographics import IDemographicsForm
from schooltool.basicperson.demographics import TextFieldDescription
from schooltool.basicperson.demographics import BoolFieldDescription
from schooltool.basicperson.demographics import PersonDemographicsData
from schooltool.schoolyear.testing import (setUp, tearDown,
                                           provideStubUtility,
                                           provideStubAdapter)
from schooltool.basicperson.ftesting import basicperson_functional_layer


def doctest_PersonDemographicsData():
    """Tests for PersonDemographicsData

    PersonDemographicsData is a container that stores persons specific
    demographics data that users enter into the system. It is a
    persistent dict that tests for the validity of the keys before
    allowing you to write the information though so if you try writing
    to a field that was not defined in person demographics fields
    container - you will get an error.

        >>> pdd = PersonDemographicsData()
        >>> pdd['email'] = "foo@example.com"
        Traceback (most recent call last):
        ...
        InvalidKeyError: email

    On the other hand - if we add a field that is named email to the
    gradebook field storage.


        >>> app = ISchoolToolApplication(None)
        >>> IDemographicsFields(app)['email'] = TextFieldDescription("email", "Email")

    And try to set the field again - everything should work.

        >>> pdd['email'] = "foo@example.com"
        >>> pdd['email']
        'foo@example.com'

    If we try to get the information for a field that has no value
    set, we should get None:

        >>> pdd['ethnicity'] is None
        True

    On the other hand - if the field was not defined in the
    demographics fields container we will get a key error:

        >>> pdd['weight']
        Traceback (most recent call last):
        ...
        KeyError: 'weight'

    """


def doctest_getPersonDemographics():
    """Tests for Person Demographics adapter

    You should be able to adapt a person to IDemographics

        >>> app = ISchoolToolApplication(None)
        >>> john = BasicPerson("johansen", "John", "Johansen")
        >>> IDemographics(john)
        <...basicperson.demographics.PersonDemographicsData object at ...>: {}

    The demographics object is being stored in the demographics object
    container and if we try to access it again we will get the same
    object:

        >>> ddc = app['schooltool.basicperson.demographics_data']
        >>> ddc['johansen'] is IDemographics(john)
        True

    """


def doctest_removePersonDemographicsSubscriber():
    """Tests for removed person subscriber

    Add a person and ensure it has demographics

        >>> app = ISchoolToolApplication(None)
        >>> persons = app['persons']
        >>> persons['johansen'] = john = BasicPerson("johansen", "John", "Johansen")

        >>> IDemographics(john)
        <...basicperson.demographics.PersonDemographicsData object at ...>: {}

        >>> ddc = app['schooltool.basicperson.demographics_data']
        >>> ddc['johansen'] is IDemographics(john)
        True

    If we remove the person, its demographics is removed

        >>> del persons['johansen']
        >>> ddc.get('johansen', None) is None
        True

    """


def doctest_DemographicsFormAdapter():
    """Tests for DemographicsFormAdapter

    When we adapt a person into a demographics we can assign all the
    demographics attributes to the person directly.

        >>> john = BasicPerson("johansen", "John", "Johansen")
        >>> form = IDemographicsForm(john)
        >>> form.ID = "an ID"

    And it will get automatically stored in that persons demographics
    data:

        >>> IDemographics(john)['ID']
        'an ID'

    """


def doctest_setUpDefaultDemographics():
    """Tests for DemographicsFormAdapter

    If there is no demographics container in the application one get's
    created and populated automatically.

        >>> app = ISchoolToolApplication(None)
        >>> del app['schooltool.basicperson.demographics_fields']
        >>> setUpDefaultDemographics(app)

        >>> app['schooltool.basicperson.demographics_fields'].keys()
        ['ID', 'ethnicity', 'language', 'placeofbirth', 'citizenship']

    """


def doctest_DemographicsFields():
    """Tests for DemographicsFields

    DemographicsFields is a class that contains demo fields that themselves
    may or may not be limited to a group or groups.

        >>> dfs = IDemographicsFields(ISchoolToolApplication(None))
        >>> dfs['email'] = TextFieldDescription("email", "Email")
        >>> dfs['supervisor'] = TextFieldDescription("supervisor", "Supervisor",
        ...     limit_keys=['teachers'])
        >>> dfs['advisor'] = TextFieldDescription("advisor", "Advisor",
        ...     limit_keys=['students'])
        >>> dfs['phone'] = TextFieldDescription("phone", "Phone",
        ...     limit_keys=['teachers', 'students'])


    When we pass the filter_key method a key that does not belong
    to any of the limit_keys lists, then it will only return those
    fields that have empty limit_keys lists.

        >>> [f.__name__ for f in dfs.filter_key('anything')]
        [u'ID', u'ethnicity', u'language', u'placeofbirth', u'citizenship',
                u'email']

    When we pass 'teachers', it picks up the additional fields that are for
    teachers.

        >>> [f.__name__ for f in dfs.filter_key('teachers')]
        [u'ID', u'ethnicity', u'language', u'placeofbirth', u'citizenship',
                u'email', u'supervisor', u'phone']

    When we pass 'students', it picks up the additional fields that are for
    students.

        >>> [f.__name__ for f in dfs.filter_key('students')]
        [u'ID', u'ethnicity', u'language', u'placeofbirth', u'citizenship',
                u'email', u'advisor', u'phone']

    We also have a filter_keys method to return fields whose keys are in the
    list passed.

        >>> [f.__name__ for f in dfs.filter_keys([])]
        [u'ID', u'ethnicity', u'language', u'placeofbirth', u'citizenship',
                u'email']

        >>> [f.__name__ for f in dfs.filter_keys(['students'])]
        [u'ID', u'ethnicity', u'language', u'placeofbirth', u'citizenship',
                u'email', u'advisor', u'phone']

        >>> [f.__name__ for f in dfs.filter_keys(['teachers'])]
        [u'ID', u'ethnicity', u'language', u'placeofbirth', u'citizenship',
                u'email', u'supervisor', u'phone']

        >>> [f.__name__ for f in dfs.filter_keys(['students', 'teachers'])]
        [u'ID', u'ethnicity', u'language', u'placeofbirth', u'citizenship',
                u'email', u'supervisor', u'advisor', u'phone']
    """


def doctest_EnumFieldDescription():
    """Tests for EnumFieldDescription

    Enum field description is a class that defines a choice field
    shown in person add/edit form.

       >>> fd = EnumFieldDescription("ethnicity", "Ethnicity")
       >>> fd.__name__ = 'ethnicity'
       >>> fields = fd.makeField()
       >>> len(fields)
       1

       >>> field = fields['ethnicity']
       >>> field
       <Field 'ethnicity'>

       >>> field.interface
       <InterfaceClass schooltool.basicperson.demographics.IDemographicsForm>

       >>> field.field
       <zope.schema._field.Choice object at ...>

       >>> field.__name__
       'ethnicity'

    """


def doctest_IntFieldDescription():
    """Tests for IntFieldDescription

    Int field description is a class that defines minimum and maximum
    values for an integer field shown in person add/edit form.

       >>> fd = IntFieldDescription("tablets", "Tablets")
       >>> fd.__name__ = 'tablets'
       >>> fd.min_value = 2
       >>> fd.max_value = 3
       >>> fields = fd.makeField()
       >>> len(fields)
       1

       >>> field = fields['tablets']
       >>> field
       <Field 'tablets'>

       >>> field.interface
       <InterfaceClass schooltool.basicperson.demographics.IDemographicsForm>

       >>> field.field
       <zope.schema._bootstrapfields.Int object at ...>

       >>> field.__name__
       'tablets'

       >>> field.field.min
       2
       >>> field.field.max
       3

    """


def doctest_TextFieldDescription():
    """Tests for TextFieldDescription

    Enum field description is a classthat defines a text field shown
    in person add/edit form.

       >>> fd = TextFieldDescription("ID", "ID")
       >>> fd.__name__ = 'ID'
       >>> fields = fd.makeField()
       >>> len(fields)
       1

       >>> field = fields['ID']
       >>> field
       <Field 'ID'>

       >>> field.interface
       <InterfaceClass schooltool.basicperson.demographics.IDemographicsForm>

       >>> field.field
       <zope.schema._bootstrapfields.TextLine object at ...>

       >>> field.__name__
       'ID'

    """


def doctest_BoolFieldDescription():
    """Tests for BoolFieldDescription

    Boolean field description is a class that defines a boolean field shown
    in person add/edit form.

       >>> fd = BoolFieldDescription("ID", "ID")
       >>> fd.__name__ = 'ID'
       >>> fields = fd.makeField()
       >>> len(fields)
       1

       >>> field = fields['ID']
       >>> field
       <Field 'ID'>

       >>> field.interface
       <InterfaceClass schooltool.basicperson.demographics.IDemographicsForm>

       >>> field.field
       <zope.schema._bootstrapfields.Bool object at ...>

       >>> field.__name__
       'ID'

    """


def doctest_DateFieldDescription():
    """Tests for DateFieldDescription

    Date field description is a class that that defines a date field
    shown in person add/edit form.

       >>> fd = DateFieldDescription("birthday", "Birth date")
       >>> fd.__name__ = 'birthday'
       >>> fields = fd.makeField()
       >>> len(fields)
       1

       >>> field = fields['birthday']
       >>> field
       <Field 'birthday'>

       >>> field.interface
       <InterfaceClass schooltool.basicperson.demographics.IDemographicsForm>

       >>> field.field
       <zope.schema._field.Date object at ...>

       >>> field.__name__
       'birthday'

    """


def test_suite():
    optionflags = doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS
    suite = doctest.DocTestSuite(optionflags=optionflags,
                                 extraglobs={'provideAdapter': provideStubAdapter,
                                             'provideUtility': provideStubUtility},
                                 setUp=setUp, tearDown=tearDown)
    suite.layer = basicperson_functional_layer
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
