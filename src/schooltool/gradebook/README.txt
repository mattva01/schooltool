=============
The Gradebook
=============

Traditionally, the gradebook is a simple spreadsheet where the columns are the
activities to be graded and each row is a student. Since SchoolTool is an
object-oriented application, we have the unique oppurtunity to implement it a
little bit different and to provide some unique features.

Categories
----------

When the SchoolTool instance is initially setup, it is part of the
administations job to setup activity categories. Activity categories can be
"homework", "paper", "test", "final exam", etc.

    >>> from schooltool.testing import setup
    >>> school = setup.setupSchoolToolSite()

By default, some categories should be available in the vocabulary. Since this
is a test, we have to set them up manually:

    >>> from schooltool.testing import registry
    >>> registry.setupDefaultCategories(school)

The categories are managed by a special option storage vocabulary. As soon as
the SchoolTool application is registered as a site, the vocabulary can be
easily initiated.

    >>> from schooltool.gradebook import category
    >>> categories = category.CategoryVocabulary()

We can now see the default categories:

    >>> sorted([term.title for term in categories])
    [u'Assignment', u'Essay', u'Exam', u'Homework', u'Journal', u'Lab',
     u'Presentation', u'Project']

The actual categories, however, are not managed by the vocabulary directly,
but by an option storage dictionary. The category module provides a high-level
function to get the dictionary:

    >>> dict = category.getCategories(school)

Now we can add,

    >>> dict.addValue('quiz', 'en', u'Quiz')
    >>> sorted([term.title for term in categories])
    [u'Assignment', u'Essay', u'Exam', u'Homework', u'Journal', u'Lab',
     u'Presentation', u'Project', u'Quiz']

delete,

    >>> dict.delValue('quiz', 'en')
    >>> sorted([term.title for term in categories])
    [u'Assignment', u'Essay', u'Exam', u'Homework', u'Journal', u'Lab',
     u'Presentation', u'Project']

and query values:

    >>> dict.getValue('assignment','en')
    u'Assignment'

    >>> dict.getValue('faux','en')
    Traceback (most recent call last):
    ...
    KeyError: 'Invalid row/column pair'

    >>> dict.queryValue('faux','en', default=u'default')
    u'default'

    >>> sorted(dict.getKeys())
    ['assignment', 'essay', 'exam', 'homework', 'journal', 'lab',
     'presentation', 'project']

As you can see, the option storage also supports multiple languages, though
only English is currently supported. (Of course, administrators can delete all
default categories and register new ones in their favorite language.)


Activities
----------

Activities are items that can be graded. In other software they are also
referred to as assignments or grading items. Activities can be defined for
courses and sections.

Let's say we have an introductory algebra course:

    >>> from schooltool.course import course
    >>> alg1 = course.Course('Alg1', 'Algebra 1')

We would like to mandate now that everyone teaching Algebra 1 must give a
final exam. To do this we get the activities for the course,

    >>> from schooltool.gradebook import interfaces
    >>> alg1_act = interfaces.IActivities(alg1)

and then add the activity:

    >>> from schooltool.gradebook import activity
    >>> from schooltool.requirement import scoresystem
    >>> alg1_act['finalExam'] = activity.Activity(
    ...     title=u'Final',
    ...     description=u'Final Exam',
    ...     category=u'Exam',
    ...     scoresystem=scoresystem.PercentScoreSystem)
    >>> final = alg1_act['finalExam']

Besides the title and description, one must also specify the category and the
score system. The category is used to group similar activities together and
later facilitate in computing the final grade. The score system is an object
describing the type of score that can be associated with the activity. In our
case it will be a percentage.

Now that we have created a course and added activities, let's now add a
section:

    >>> from schooltool.course import section
    >>> sectionA = section.Section('Alg1-A')
    >>> alg1.sections.add(sectionA)

We also want to have some students in the class,

    >>> from schooltool.person import person
    >>> tom = person.Person('tom', 'Tom Hoffman')
    >>> sectionA.members.add(tom)
    >>> paul = person.Person('paul', 'Paul Cardune')
    >>> sectionA.members.add(paul)
    >>> claudia = person.Person('claudia', 'Claudia Richter')
    >>> sectionA.members.add(claudia)

as well as a teacher:

    >>> stephan = person.Person('stephan', 'Stephan Richter')
    >>> sectionA.instructors.add(stephan)

Now we can add activities to the section using the same API as for the course:

    >>> import datetime
    >>> sectionA_act = interfaces.IActivities(sectionA)
    >>> sectionA_act['hw1'] = activity.Activity(
    ...     title=u'HW 1',
    ...     description=u'Homework 1',
    ...     category=u'Assginment',
    ...     scoresystem=scoresystem.RangedValuesScoreSystem(max=10),
    ...     date=datetime.date(2006, 2, 10))
    >>> hw1 = sectionA_act['hw1']

    >>> sectionA_act['hw2'] = activity.Activity(
    ...     title=u'HW 2',
    ...     description=u'Homework 2',
    ...     category=u'Assginment',
    ...     scoresystem=scoresystem.RangedValuesScoreSystem(max=15),
    ...     date=datetime.date(2006, 4, 15))
    >>> hw2 = sectionA_act['hw2']

In this case we create a new score system. This is very typical for those type
of assignments, since their score commonly varies. There is also an optional
argument, ``date``, that allows you to specify the date of the activity. This
can either be interpreted as the due date or the date an exam is taken.

We can also look at the activities that we defined:

    >>> sorted(sectionA_act.items())
    [('finalExam', InheritedRequirement(<Activity u'Final'>)),
     ('hw1', <Activity u'HW 1'>), ('hw2', <Activity u'HW 2'>)]

As you can see, the section *always* inherits the activities from the
course.


Evaluations
-----------

Now that all of our activities have been defined, we can finally enter some
grades using the gradebook.

    >>> from schooltool.gradebook import interfaces
    >>> gradebook = interfaces.IGradebook(sectionA)

Let's enter some grades:

    >>> gradebook.evaluate(student=tom, activity=hw1, score=8)
    >>> gradebook.evaluate(student=paul, activity=hw1, score=10)
    >>> gradebook.evaluate(student=claudia, activity=hw1, score=7)

    >>> gradebook.evaluate(student=tom, activity=hw2, score=10)
    >>> gradebook.evaluate(student=paul, activity=hw2, score=12)
    >>> gradebook.evaluate(student=claudia, activity=hw2, score=14)

    >>> gradebook.evaluate(student=tom, activity=final, score=85)
    >>> gradebook.evaluate(student=paul, activity=final, score=99)
    >>> gradebook.evaluate(student=claudia, activity=final, score=90)

Of course there are some safety precautions:

1. You cannot add a grade for someone who is not in the section:

    >>> marius = person.Person('marius', 'Marius Gedminas')
    >>> gradebook.evaluate(student=marius, activity=final, score=99)
    Traceback (most recent call last):
    ...
    ValueError: Student 'marius' is not in this section.

2. You cannot add a grade for an activity that does not belong to the section:

    >>> hw3 = activity.Activity(
    ...     title=u'HW 3',
    ...     category=u'Assginment',
    ...     scoresystem=scoresystem.RangedValuesScoreSystem(max=10))

    >>> gradebook.evaluate(student=claudia, activity=hw3, score=8)
    Traceback (most recent call last):
    ...
    ValueError: u'HW 3' is not part of this section.

3. You cannot add a grade that is not a valid value of the score system:

    >>> gradebook.evaluate(student=claudia, activity=hw2, score=-8)
    Traceback (most recent call last):
    ...
    ValueError: -8 is not a valid score.

    >>> gradebook.evaluate(student=claudia, activity=hw2, score=16)
    Traceback (most recent call last):
    ...
    ValueError: 16 is not a valid score.

There are a couple more management functions that can be used to maintain the
evaluations. For example, you can ask whether an evaluation for a particular
student and activity has been made:

    >>> gradebook.hasEvaluation(student=tom, activity=hw1)
    True

You can then also delete evaluations:

    >>> gradebook.removeEvaluation(student=tom, activity=hw1)
    >>> gradebook.hasEvaluation(student=tom, activity=hw1)
    False

The gradebook also provides a simple, but powerful query function that allows
you to look up the rows, columns or single cells of the virtual gradebook
spreadsheet:

    >>> sorted(gradebook.getEvaluationsForStudent(paul),
    ...        key=lambda x: x[0].title)
    [(<Activity u'Final'>, <Evaluation for <Activity u'Final'>, value=99>),
     (<Activity u'HW 1'>, <Evaluation for <Activity u'HW 1'>, value=10>),
     (<Activity u'HW 2'>, <Evaluation for <Activity u'HW 2'>, value=12>)]

    >>> sorted(gradebook.getEvaluationsForActivity(hw2),
    ...        key=lambda x: x[0].username)
    [(<...Person ...>, <Evaluation for <Activity u'HW 2'>, value=14>),
     (<...Person ...>, <Evaluation for <Activity u'HW 2'>, value=12>),
     (<...Person ...>, <Evaluation for <Activity u'HW 2'>, value=10>)]

    >>> gradebook.getEvaluation(tom, hw2)
    <Evaluation for <Activity u'HW 2'>, value=10>

Statistics
----------

The gradebook comes also with a simple statistics package. The statistics are
an adapter of the gradebook:

    >>> statistics = interfaces.IStatistics(gradebook)

You can now calculate the basic statistics:

- The average grade of an activity:

    >>> statistics.calculateAverage(hw2)
    12.0

- The average grade as a percentage:

    >>> statistics.calculatePercentAverage(hw2)
    80.0

- The median of an activity:

    >>> statistics.calculateMedian(hw2)
    12.0

- The standard deviation of an activity:

    >>> statistics.calculateStandardDeviation(hw2)
    2.0

- The variance of the activity:

    >>> statistics.calculateVariance(hw2)
    4.0

Okay, that's pretty much it. The statistics represent computations on the
columns of the virtual spreadsheets. To make meaningful computations for the
rows -- in other words computing the final grade of a student -- we need to
work a little bit harder.


Weight Scales
-------------

To be done later.


Sorting Activities
------------------

To be done later.
