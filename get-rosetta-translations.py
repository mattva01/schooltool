#!/usr/bin/python
#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2005    Shuttleworth Foundation
#                       Brian Sutherland
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
Script to download the latest translations from rosetta.

It assumes that rosetta is the cannonical source of translations.
"""

import os
import urllib2

here=os.path.dirname(__file__)

#
# Configuration
#

# Translations to download, these are the rosetta translations which have had
# some work on them
locales=["af",
         "ca",
         "de",
         "de_CH",
         "es_MX",
         "es_ES",
         "en_US",
         "fr",
         "fr_CA",
         "fr_FR",
         "he",
         "it",
         "lt",
         "nl",
         "pl",
         "pt_PT",
         "sv"
         ]

rosetta_url = "https://launchpad.ubuntu.com/products/$domain$/unknown/+pots/$domain$-ui/$locale$/po"

translation_dir = os.path.join(here, 'src', 'schoolbell', 'app', 'locales',
        "$locale$", "LC_MESSAGES", "$domain$.po")

create_dir = True

domain = "schoolbell"

#

print """WARNING: This script does no data verification or po file merging,
it simply downloads the file from rosetta.

It would be a very good idea to manually check the translations before
committing them to ensure no data loss.
"""

for locale in locales:
    # setup filename and url
    tmp = translation_dir.replace("$locale$", locale)
    filename = tmp.replace("$domain$", domain)
    url = rosetta_url.replace("$locale$", locale).replace("$domain$", domain)
    # Get the target filename, optionally creating directories
    print "saving %s \nin %s" % (url, filename)
    if not os.path.exists(os.path.dirname(filename)):
        if create_dir:
            os.makedirs(os.path.dirname(filename))
            print "     created dir."
        else:
            print "     create_dir set to FALSE."
            print "ERROR: no directory to put translation, ignoring."
            continue
    # Download the translation .po
    url_obj = urllib2.urlopen(url)
    data = url_obj.read()
    url_obj.close()
    print "    read."
    # Save it to the file
    file = open(filename, 'w')
    file.write(data)
    file.close()
    print "    saved."
