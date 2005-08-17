# Make a package.

def registerTestSetup():
    from zope.interface import classImplements
    from schoolbell.app.testing import registry

    def addPersonContainer(app):
        from schoolbell.app.person import person
        app['persons'] = person.PersonContainer()
    registry.register('ApplicationContainers', addPersonContainer)

    def haveCalendar():
        from schoolbell.app.person import person
        from schoolbell.app.interfaces import IHaveCalendar
        if not IHaveCalendar.implementedBy(person.Person):
            classImplements(person.Person, IHaveCalendar)
    registry.register('CalendarComponents', haveCalendar)

registerTestSetup()
del registerTestSetup

