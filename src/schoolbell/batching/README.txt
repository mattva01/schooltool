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

    >>> from schoolbell.batching.tests.sample.browser import BatchView
    >>> View = SimpleViewClass('tests/sample/view.pt', bases=(BatchView,))

    >>> from schoolbell.batching.tests.sample import data
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


If we are on the first batch, the 'previous' text is contained in a span, while
the 'next' text is a link:

    >>> print view()
    <BLANKLINE>
    ...
          <span class="previous">
            &laquo; <span>Previous</span>
            <span>10</span>
          </span>
    ...
          <a class="next"
             href="?batch_start=10&amp;batch_size=10">
            <span>Next</span>
            <span>10</span> &raquo;
          </a>
    ...

If we go to the next batch, we will see a link back to the first batch

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


