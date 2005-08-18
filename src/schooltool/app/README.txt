SchoolTool currently provides a SchoolBell based calendar server that adds
school specific features.  In addition to the basic SchoolBell Person, Groups,
and Resources, SchoolTool adds Course and Sections.

We need some test setup:

    >>> from schooltool.testing import setup
    >>> from schooltool.relationship.tests import setUp, tearDown
    >>> setUp()
    >>> from schooltool.group.group import Group
    >>> from schooltool.person.person import Person, PersonContainer
    >>> from schooltool import app
    >>> from schooltool.course.course import Course
    >>> from schooltool.course.section import Section

    >>> school = setup.createSchoolBellApplication()

    >>> school['courses']
    <schooltool.course.course.CourseContainer object at ...>
    >>> school['sections']
    <schooltool.course.section.SectionContainer object at ...>

A Course is a simple object with a title and description that can describe a
particular course of study.

    >>> ushistory = Course(title="US History", description="Years 1945 - 2000")
    >>> school['courses']['ushistory'] = ushistory

    >>> ushistory.title
    'US History'

    >>> ushistory.description
    'Years 1945 - 2000'

The educational material covered by a course is taught to sets of students in
Sections.  Each section is related to the Course with the CourseSections
relationship and the list of sections can be accessed via the Course.sections
RelationshipProperty.

We haven't set up any sections yet so:

    >>> [section.title for section in ushistory.sections]
    []

is empty.  Let's create some sections and add them to US History.

    >>> school['sections']['section1'] = section1 = Section(title="Section 1")
    >>> school['sections']['section2'] = section2 = Section(title="Section 2")
    >>> ushistory.sections.add(section1)
    >>> ushistory.sections.add(section2)
    >>> [section.title for section in ushistory.sections]
    ['Section 1', 'Section 2']

Each section represents a particular set of students meeting with a particular
instructor at a particular time to cover the course material.

    >>> school['persons']['teacher1'] = teacher1 = Person('Teacher1')
    >>> school['persons']['teacher2'] = teacher2 = Person('Teacher2')
    >>> school['persons']['student1'] = student1 = Person('Student1')
    >>> school['persons']['student2'] = student2 = Person('Student2')
    >>> school['persons']['student3'] = student3 = Person('Student3')
    >>> school['persons']['student4'] = student4 = Person('Student4')

The teacher of a section is defined with the Instruction relationship and can
be accessed via the section.instructors RelationshipProperty:

    >>> from schooltool.relationships import Instruction
    >>> [teacher.username for teacher in section1.instructors]
    []
    >>> Instruction(instructor=teacher1, section=section1)
    >>> [teacher.username for teacher in section1.instructors]
    ['Teacher1']

sections can have more than one instructor:

    >>> section1.instructors.add(teacher2)
    >>> [teacher.username for teacher in section1.instructors]
    ['Teacher1', 'Teacher2']


You can determine if a Person is a teacher using schooltool.relationship
methods, there is also a method PersonView.isTeacher in schooltool's web UI:

    >>> from schooltool.relationships import URISection, URIInstruction
    >>> from schooltool.relationship import getRelatedObjects
    >>> len(getRelatedObjects(teacher1, URISection,
    ...                       rel_type=URIInstruction)) > 0
    True

sections students are associated with a section via the Membership
relationship from SchoolBell or via the section.members property.  The section
itself participates in the Membership relationship in the URIGroup role which
is possible because Sections implement the IGroup interface.

    >>> [student.username for student in section1.members]
    []
    >>> from schooltool.app.membership import Membership
    >>> Membership(group=section1, member=student1)
    >>> Membership(group=section1, member=student2)
    >>> [student.username for student in section1.members]
    ['Student1', 'Student2']

We can use Groups to add multiple students to a section to keep the group of
students together, similar to the "Form" concept used in some US Primary
schools.

    >>> school['groups']['form1'] = form1 = Group(title="Form1")
    >>> form1.members.add(student3)
    >>> form1.members.add(student4)
    >>> section2.members.add(form1)
    >>> [form.title for form in section2.members]
    ['Form1']

Checking for a person's status as a student is also handled with the
schooltool.relationship methods.  There are convenience methods in PersonView
as well:

    >>> from schooltool.app.membership import URIGroup, URIMembership
    >>> from schooltool.course.interfaces import ISection
    >>> for obj in getRelatedObjects(student2, URIGroup,
    ...                              rel_type=URIMembership):
    ...     ISection.providedBy(obj)
    True

See schooltool.browser.app for showing individual members of the form in the
UI.

Sections can be part of more than 1 course and sections have a courses
RelatioshipProperty to list what courses they implement.

    >>> amlit = Course(title="American Literature",
    ...                    description="Taught with US History")
    >>> school['courses']['almit'] = ushistory
    >>> amlit.sections.add(section1)
    >>> [section.title for section in amlit.sections]
    ['Section 1']
    >>> [course.title for course in section1.courses]
    ['US History', 'American Literature']

    >>> tearDown()

