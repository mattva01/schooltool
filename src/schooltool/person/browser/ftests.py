from schooltool.app.testing import app_functional_layer
from schooltool.testing.functional import collect_ftests

def test_suite():
    return collect_ftests(layer=app_functional_layer)
