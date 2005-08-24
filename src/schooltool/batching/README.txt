Batching large sets
===================

Batching provides a way for you to split a large set of data into smaller sets
(batches) for presentation in a UI

We have created a sample package in tests.sample, lets see how it works

First we need a little setup

    >>> from zope.app.testing import ztapi, setup
    >>> from zope.app.traversing.namespace import view
    >>> from zope.app.traversing.interfaces import ITraversable
    >>> setup.setUpTraversal()
    >>> ztapi.provideView(None, None, ITraversable, 'view', view)
    >>> from zope.app.pagetemplate.simpleviewclass import SimpleViewClass
    >>> ztapi.browserView(None, 'batch_macros', SimpleViewClass("macros.pt"))

Now we can create our view

    >>> from schooltool.batching.tests.sample.browser import BatchView
    >>> View = SimpleViewClass('tests/sample/view.pt', bases=(BatchView,))

    >>> from schooltool.batching.tests.sample import data
    >>> from zope.publisher.browser import TestRequest
    >>> view = View(data, TestRequest())
    >>> view.update()


Navigation
----------

The batch navigation bar links to the previous and next batches. In TAL you can
call the macro like this:

    <tal:block define="batch view/batch">
        <metal:macro use-macro="view/@@batch_macros/batch-navigation"/>
    </tal:block>

This will give you a navigation bar that (after CSS is applied) looks roughly
like this:

 +----------------------------------------------------+----------------------+
 | << previous 10         1 2 3 4 5        next 10 >> | show more   show all |
 +----------------------------------------------------+----------------------+


The 'previous' link will not actually be a link if there is no previous batch 
(if we are on the first batch) and there will also be no number displayed for 
the same reason.

    >>> print view()
    <BLANKLINE>
    ...
          <span class="previous">
            &laquo; <span>Previous</span>
          </span>
    ...
          <a class="next"
             href="?batch_start=10&amp;batch_size=10">
            <span>Next</span>
            <span>10</span> &raquo;
          </a>
    ...

If we go to the next batch, we will see a link back to the first batch.

    >>> view.batch = view.batch.next()
    >>> print view()
    <BLANKLINE>
    ...
          <a class="previous"
             href="?batch_start=0&amp;batch_size=10">
            &laquo; <span>Previous</span>
            <span>10</span>
          </a>
    ...
          <a class="next"
             href="?batch_start=20&amp;batch_size=10">
            <span>Next</span>
            <span>10</span> &raquo;
          </a>
    ...

If we go to the last batch, we will get the same behavior with the 'next' link:

    >>> view.batch = view.batch.batches()[-1]
    >>> print view()
    <BLANKLINE>
    ...
          <a class="previous"
             href="?batch_start=30&amp;batch_size=10">
            &laquo; <span>Previous</span>
            <span>10</span>
          </a>
    ...
          <span class="next">
            <span>Next</span> &raquo;
          </span>
    ...

If we are not on the last batch, the number for 'next' represents how many
items are left in the batch (how many will be displayed on the last page):

    >>> view.batch = view.batch.prev()
    >>> print view()
    <BLANKLINE>
    ...
          <a class="previous"
             href="?batch_start=20&amp;batch_size=10">
            &laquo; <span>Previous</span>
            <span>10</span>
          </a>
    ...
          <a class="next"
             href="?batch_start=40&amp;batch_size=10">
            <span>Next</span>
            <span>1</span> &raquo;
          </a>
    ...
