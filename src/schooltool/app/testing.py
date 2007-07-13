import os
from schooltool.testing.functional import ZCMLLayer

here = os.path.dirname(__file__)

app_functional_layer = ZCMLLayer(os.path.join(here, 'ftesting.zcml'),
                                 __name__,
                                 'app_functional_layer')
