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

def makeDecimalARock():
    # XXX this is insecure
    from decimal import Decimal
    from zope.security.checker import NoProxy
    import zope.security
    zope.security.checker.BasicTypes[Decimal] = NoProxy

makeDecimalARock()
del makeDecimalARock
