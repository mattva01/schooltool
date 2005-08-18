# Make a package.

def registerTestSetup():
    from zope.interface import classImplements
    from schooltool.testing import registry

    def addCourseAndSectionContainer(app):
        from schooltool.course import course, section
        app['courses'] = course.CourseContainer()
        app['sections'] = section.SectionContainer()
    registry.register('ApplicationContainers', addCourseAndSectionContainer)

    def haveCalendar():
        from schooltool.course import section
        from schooltool.app.interfaces import IHaveCalendar
        if not IHaveCalendar.implementedBy(section.Section):
            classImplements(section.Section, IHaveCalendar)
    registry.register('CalendarComponents', haveCalendar)

registerTestSetup()
del registerTestSetup
