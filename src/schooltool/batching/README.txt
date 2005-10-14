Batching large sets
===================

Batching provides a way for you to split a large set of data into smaller sets
(batches) for presentation in a UI.

The view class should provide a batch for the template::

    from schooltool.batching import Batch

    class SomeView(BrowserView):
        ...

        def update(self):
            data = [...the full list of items...]
            start = int(self.request.get('batch_start', 0))
            size = int(self.request.get('batch_size', 10))
            self.batch = Batch(data, start, size)

In the page template you will want to include the batch navigation macro,
and use tal:repeat on view/batch instead of iterating over the full list.
(Make sure the template calls view/update before accessing view/batch.) ::

    <tal:block define="batch view/batch">
      <metal:macro use-macro="view/@@batch_macros/batch-navigation"/>
      <!-- Here goes your data, for example:
           <ul>
             <li tal:repeat="item batch" tal:content="item"/>
           </ul>
      -->
    </tal:block>

This will give you a navigation bar that (after CSS is applied) looks roughly
like this:

    +-------------------------------------------------------------+----------+
    | << Previous 10    1 ... 4 5 6 7 8 9 10 ... 15    next 10 >> | Show All |
    +-------------------------------------------------------------+----------+

