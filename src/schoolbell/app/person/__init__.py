# Make a package.

def registerTestSetup():
    from schoolbell.app.testing import registry

    def addPersonContainer(app):
        from schoolbell.app.person import person
        app['persons'] = person.PersonContainer()

    registry.register('ApplicationContainers', addPersonContainer)

registerTestSetup()
del registerTestSetup

