#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2005 Shuttleworth Foundation
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
Unit tests for schoolbell.batching.batch

$Id$
"""

import unittest

from zope.testing import doctest

def doctest_Batch():
    """Test for Batch.

    Batching lets us split up a large list of information into smaller, more
    presentable lists.

    First we'll create a set of junk information that we can play with.

      >>> testData = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]

    Now we can feed this to our Batch class.

      >>> from schoolbell.batching.batch import Batch
      >>> batch = Batch(testData, 0, 3)

    Our 'batch' instance is now loaded up with our testData. The batch starts
    at the first element in the testData list and holds the first 3 items:

      >>> [item for item in batch]
      [1, 2, 3]
      >>> len(batch)
      3

    We can also fetch the first and last items in the batch which can be useful
    when building page navigation (if your list is sorted):

      >>> batch.first()
      1
      >>> batch.last()
      3

    We can also see how many batches it will take to cover our list of 14 items

      >>> batch.numBatches()
      5

    Note that the the starting point for the batch is irrelevant when
    calcualting how many batches are required for a list:

      >>> batch = Batch(testData, 10, 3)
      >>> batch.numBatches()
      5

    We can also see if an item is in our batch.  With our starting point at the
    10th item ('11'), '11' should be in our batch but '1' should not:

      >>> [item for item in batch]
      [11, 12, 13]
      >>> 11 in batch
      True
      >>> 1 in batch
      False

    Batches are navigated through the prev() and next() methods:

      >>> batch.start
      10
      >>> nbatch = batch.next()
      >>> nbatch.start
      13
      >>> pbatch = batch.prev()
      >>> pbatch.start
      7

    It's also important that our batches don't overlap

      >>> [item for item in pbatch]
      [8, 9, 10]
      >>> [item for item in batch]
      [11, 12, 13]
      >>> [item for item in nbatch]
      [14]

    If there is no previous or next batch, we get None:

      >>> batch = Batch(testData, 0, 10)
      >>> print batch.prev()
      None

      >>> batch = Batch(testData, len(testData) - 1, 10)
      >>> [item for item in batch]
      [14]
      >>> print batch.next()
      None

    We can also comapre two batches to see if they are or are not equal:

      >>> batch1 = Batch(testData, 0, 10)
      >>> batch2 = Batch(testData, 0, 10)
      >>> batch1 == batch2
      True
      >>> batch1 != batch2
      False

      >>> batch1 = batch1.next()
      >>> batch1 == batch2
      False
      >>> batch1 != batch2
      True

      >>> batch2 = batch2.next()
      >>> batch1 == batch2
      True
      >>> batch1 != batch2
      False

    """

def test_suite():
    return unittest.TestSuite([
                doctest.DocTestSuite(optionflags=doctest.ELLIPSIS),
                doctest.DocTestSuite('schoolbell.batching.batch'),
           ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
