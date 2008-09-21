# Make a package.

def registerTestSetup():
    from zope.interface import classImplements
    from schooltool.testing import registry

    def haveCalendar():
        from schooltool.course import section
        from schooltool.app.interfaces import IHaveCalendar
        if not IHaveCalendar.implementedBy(section.Section):
            classImplements(section.Section, IHaveCalendar)
    registry.register('CalendarComponents', haveCalendar)

    def ownTimetables():
        from schooltool.course import section
        from schooltool.timetable.interfaces import IOwnTimetables
        if not IOwnTimetables.implementedBy(section.Section):
            classImplements(section.Section, IOwnTimetables)

    registry.register('TimetablesComponents', ownTimetables)

    def bookResources():
        from schooltool.course import section
        from schooltool.timetable.interfaces import IBookResources
        if not IBookResources.implementedBy(section.Section):
            classImplements(section.Section, IBookResources)

    registry.register('TimetablesComponents', bookResources)

registerTestSetup()
del registerTestSetup

