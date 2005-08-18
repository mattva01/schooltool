# Make a package.

def registerTestSetup():
    from zope.interface import classImplements
    from schooltool.testing import registry

    def addPersonContainer(app):
        from schooltool.person import person
        app['persons'] = person.PersonContainer()
    registry.register('ApplicationContainers', addPersonContainer)

    def haveCalendar():
        from schooltool.person import person
        from schooltool.app.interfaces import IHaveCalendar
        if not IHaveCalendar.implementedBy(person.Person):
            classImplements(person.Person, IHaveCalendar)
    registry.register('CalendarComponents', haveCalendar)

registerTestSetup()
del registerTestSetup

