# Make a package.

def registerTestSetup():
    from zope.interface import classImplements
    from schooltool.testing import registry

    def addResourceContainer(app):
        from schooltool.resource import resource
        app['resources'] = resource.ResourceContainer()
    registry.register('ApplicationContainers', addResourceContainer)

    def haveCalendar():
        from schooltool.resource import resource
        from schooltool.app.interfaces import IHaveCalendar
        if not IHaveCalendar.implementedBy(resource.Resource):
            classImplements(resource.Resource, IHaveCalendar)
    registry.register('CalendarComponents', haveCalendar)

registerTestSetup()
del registerTestSetup
