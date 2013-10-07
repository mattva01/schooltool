=============
The Dashboard
=============

Originally, as CanDo users found it difficult to use the Schooltool interface,
a dashboard was created to give the average user (teacher or student) quick
access to their classes without having to navigate the menu system.  It also
included functionality that no users were interested in, so in true XP fashion,
the current dashboard only contains what the current userbase wants, i.e.,
links to the teacher's or student's section gradebooks.

To test this we will create a teacher, a student, a course, and a section where
the teacher and student meet.

   >>> from schooltool.app.browser.ftests import setup
   >>> from schooltool.basicperson.browser.ftests.setup import addPerson
   >>> setup.addSchoolYear('2007', '2007-01-01', '2007-12-31')
   >>> setup.addTerm('Winter', '2007-01-01', '2007-06-01', schoolyear='2007')
   >>> addPerson(u'Teacher', 'Smith', 'teacher', 'pwd', groups=['teachers'])
   >>> addPerson(u'Student', 'Blake', 'student', 'pwd', groups=['students'])
   >>> setup.addCourse('course1', '2007')
   >>> setup.addSection('course1', '2007', 'Winter', title='section1', instructors=['Teacher'], members=['Student'])

Now we will log in as the teacher, go to the dashboard, and note there is a
link to the teacher's gradebook.

   >>> teacher = setup.logIn('teacher', 'pwd')
   >>> teacher.open('http://localhost/dashboard.html')
   >>> link = teacher.getLink('course1 section1')
   >>> link.url
   'http://localhost/schoolyears/2007/winter/sections/1/gradebook'

Finally we will log in as the student, go to the dashboard, and note there is a
link to the student's grades.

   >>> student = setup.logIn('student', 'pwd')
   >>> student.open('http://localhost/dashboard.html')
   >>> link = student.getLink('course1 section1')
   >>> link.url
   'http://localhost/schoolyears/2007/winter/sections/1/mygrades'


