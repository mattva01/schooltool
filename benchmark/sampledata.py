#!/usr/bin/python
"""
Benchmark the sample data generator.
"""

from datetime import datetime, timedelta

from benchmark import *

import transaction


def setup_benchmark():
    setup = load_ftesting_zcml()
    r = http("""POST /@@contents.html HTTP/1.1
Authorization: Basic mgr:mgrpw
Content-Length: 81
Content-Type: application/x-www-form-urlencoded

type_name=BrowserAdd__schooltool.app.app.SchoolToolApplication&new_value=frogpond""")
    assert r.getStatus() == 303

    do_generate_sampledata()


def do_generate_sampledata():
    """Benchmark the sample data generator."""
    r = http(r"""
         GET /frogpond/@@sampledata.html?seed=SchoolTool&SUBMIT= HTTP/1.1
         Authorization: Basic mgr:mgrpw
    """)
    assert r.getStatus() == 200


def main():
    print "ZCML took %.3f seconds." % measure(load_ftesting_zcml)
    print "Setup took %.3f seconds." % measure(setup_benchmark)


if __name__ == '__main__':
    main()
