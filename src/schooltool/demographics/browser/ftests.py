from schooltool.testing.functional import load_ftesting_zcml
from schooltool.testing.functional import collect_ftests

def test_suite():
    load_ftesting_zcml()
    return collect_ftests()
