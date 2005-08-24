# Just for BBB:
from zope.deprecation import deprecated

from schooltool.calendar.recurrent import DailyRecurrenceRule
from schooltool.calendar.recurrent import YearlyRecurrenceRule
from schooltool.calendar.recurrent import WeeklyRecurrenceRule
from schooltool.calendar.recurrent import MonthlyRecurrenceRule
deprecated(('DailyRecurrenceRule', 'YearlyRecurrenceRule',
            'WeeklyRecurrenceRule', 'MonthlyRecurrenceRule'),
           'This class has moved to schooltool.calendar.recurrent '
           'The reference will be gone in 0.15')
