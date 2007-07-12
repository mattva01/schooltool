#!/usr/bin/env python
"""A script that generates vcal_dict.py.

vcal_dict.py contains a dict of tuples (tzid, vcal_representation)
indexed by their pytz id.

To generate the file when new version of Olson database appears follow
these steps:

1. Download vzic source code from:

  http://dspace.dial.pipex.com/prod/dialspace/town/pipexdsl/s/asbm26/vzic/

2. Apply vzic.patch to it (the patch was created for version 1.2 of
   vzic).

3. Follow the instructions in vzic README file to generate a set of
   ics files.

4. Run this script passing the name of the generated zoneinfo
   directory as the first and only parameter.

"""

import os
import sys
from schooltool.calendar.generate_vcal_dict import main

if __name__ == "__main__":
    main(sys.argv)
