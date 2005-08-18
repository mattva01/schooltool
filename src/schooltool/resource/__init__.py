# Make a package.

def registerTestSetup():
    from zope.interface import classImplements
    from schoolbell.app.testing import registry

    def addResourceContainer(app):
        from schoolbell.app.resource import resource
        app['resources'] = resource.ResourceContainer()
    registry.register('ApplicationContainers', addResourceContainer)

    def haveCalendar():
        from schoolbell.app.resource import resource
        from schoolbell.app.interfaces import IHaveCalendar
        if not IHaveCalendar.implementedBy(resource.Resource):
            classImplements(resource.Resource, IHaveCalendar)
    registry.register('CalendarComponents', haveCalendar)

registerTestSetup()
del registerTestSetup
