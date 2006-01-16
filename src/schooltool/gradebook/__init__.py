# Make a package

def registerTestSetup():
    from zope.interface import classImplements
    from schooltool.testing import registry

    def addDefaultCategories(app):
        class FauxEvent(object):
            object = app
        from schooltool.gradebook import category
        category.addDefaultCategoriesToApplication(FauxEvent())
    registry.register('DefaultCategories', addDefaultCategories)

registerTestSetup()
del registerTestSetup
