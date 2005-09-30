=====================================================
Level Management and Academic Workflow via the Web UI
=====================================================

This document presents the management of levels and the academic career of a
student via a promotion workflow from the perspective of the Web UI.

    >>> from zope.testbrowser import Browser
    >>> browser = Browser()
    >>> browser.addHeader('Authorization', 'Basic manager:schooltool')

    >>> browser.handleErrors = False
    >>> browser.open('http://localhost/')


Level Management
----------------

First we create a couple of levels.

    >>> browser.open('http://localhost/levels')

    >>> browser.getLink('New Level').click()
    >>> browser.getControl('Title').value = u'1st Grade'
    >>> browser.getControl('Initial Level').selected = True
    >>> browser.getControl(name='add_input_name').value = u'level1'
    >>> browser.getControl('Add').click()

    >>> '1st Grade' in browser.contents
    True

    >>> browser.getLink('New Level').click()
    >>> browser.getControl('Title').value = u'2nd Grade'
    >>> browser.getControl('Initial Level').selected = False
    >>> browser.getControl(name='add_input_name').value = u'level2'
    >>> browser.getControl('Add').click()

    >>> '2nd Grade' in browser.contents
    True

Since we did not connect the two levels, validation should fail:

    >>> browser.getLink('Validate Levels').click()
    >>> browser.getControl('Validate').click()

    >>> "One or more disconnected levels detected." in browser.contents
    True
    >>> "2nd Grade" in browser.contents
    True

If we connect `level1` to `level2` and also `level2` to `level1`, we get a
loop validation error:

    >>> browser.getLink('Levels').click()
    >>> browser.getLink('1st Grade').click()
    >>> browser.getLink('Edit Info').click()
    >>> browser.getControl('Next Level').value = ['level2']
    >>> browser.getControl('Apply').click()

    >>> browser.getLink('Levels').click()
    >>> browser.getLink('2nd Grade').click()
    >>> browser.getLink('Edit Info').click()
    >>> browser.getControl('Next Level').value = ['level1']
    >>> browser.getControl('Apply').click()

    >>> browser.getLink('Levels').click()
    >>> browser.getLink('Validate Levels').click()
    >>> browser.getControl('Validate').click()

    >>> "A Level Loop Error was detected." in browser.contents
    True
    >>> print browser.contents
    <BLANKLINE>
    ...
    Simply do not specify level
    <em>1st Grade</em>
    ...

Okay, so let's do what the error tells us and remove the link in `level2` to
`level1`:

    >>> browser.getLink('Levels').click()
    >>> browser.getLink('1st Grade').click()
    >>> browser.getLink('Edit Info').click()
    >>> browser.getControl('Previous Level').value = []
    >>> browser.getControl('Apply').click()

    >>> browser.getLink('Levels').click()
    >>> browser.getLink('Validate Levels').click()
    >>> browser.getControl('Validate').click()

    >>> print browser.contents
    <BLANKLINE>
    ...
    No errors were detected.
    ...


The Academic Career of a Student
--------------------------------

Before we can do anything, we have to create a student:

    >>> import StringIO

    >>> browser.getLink('Persons').click()
    >>> browser.getLink('New Person').click()

    >>> browser.getControl('Full name').value = 'Stephan Richter'
    >>> browser.getControl('Username').value = 'srichter'
    >>> browser.getControl('Password').value = 'foobar'
    >>> browser.getControl('Verify password').value = 'foobar'
    >>> browser.getControl('Photo').value = StringIO.StringIO()
    >>> browser.getControl('Add').click()

    >>> 'Stephan Richter' in browser.contents
    True

Now we go to the manager group, and walk the student through the academic
career:

    >>> browser.getLink('Groups').click()
    >>> browser.getLink('Manager', url="groups/manager").click()
    >>> browser.getLink('Student Management').click()

We now select the student which we want to enroll in the school.

    >>> form = browser.getForm(name='enroll')
    >>> form.getControl(name='ids:list').value = ['srichter']
    >>> form.submit('Enroll')

    >>> print browser.contents
    <BLANKLINE>
    ...
    <div id="message">Students successfully enrolled.</div>
    ...
    <option value="level1">1st Grade</option>
    <option value="level2">2nd Grade</option>
    ...

Now that the student is enrolled, we can initialize him at a particular
level. Our student will enter the first grade:

    >>> form = browser.getForm(name='initialize')
    >>> ctrl = form.getControl(name='ids:list')
    >>> id = ctrl.options[0]
    >>> ctrl.value = [id]
    >>> form.getControl(name=id+'.level').value = ['level1']
    >>> form.submit('Apply')

    >>> print browser.contents
    <BLANKLINE>
    ...
    <div id="message">Student processes successfully updated.</div>
    ...
    <div class="value">
    <select id="...outcome" name="...outcome" size="1" >
    <option selected="selected" value="pass">pass</option>
    <option value="fail">fail</option>
    <option value="withdraw">withdraw</option>
    </select>
    </div>
    ...

The student passes the first grade

    >>> form = browser.getForm(name='outcome')
    >>> ctrl = form.getControl(name='ids:list')
    >>> id = ctrl.options[0]
    >>> ctrl.value = [id]
    >>> browser.getControl(name=id+'.outcome').value = ['pass']
    >>> form.submit('Apply')

    >>> print browser.contents
    <BLANKLINE>
    ...
    <div id="message">Student processes successfully updated.</div>
    ...
    <span>2nd Grade</span>
    ...

but fails the second grade the first time around:

    >>> form = browser.getForm(name='outcome')
    >>> ctrl = browser.getControl(name='ids:list', index=1)
    >>> id = ctrl.options[0]
    >>> ctrl.value = [id]
    >>> browser.getControl(name=id+'.outcome').value = ['fail']
    >>> form.submit('Apply')

    >>> print browser.contents
    <BLANKLINE>
    ...
    <div id="message">Student processes successfully updated.</div>
    ...
    <span>2nd Grade</span>
    ...

If you forget to select the student, you get a nice notice:

    >>> form = browser.getForm(name='outcome')
    >>> ctrl = form.getControl(name='ids:list')
    >>> id = ctrl.options[0]
    >>> browser.getControl(name=id+'.outcome').value = ['fail']
    >>> form.submit('Apply')

    >>> print browser.contents
    <BLANKLINE>
    ...
    <div id="message">No students were selected.</div>
    ...

Now we finally pass the student, so he will graduate; that means he will
appear at the top of the list again:

    >>> form = browser.getForm(name='outcome')
    >>> ctrl = form.getControl(name='ids:list')
    >>> id = ctrl.options[0]
    >>> ctrl.value = [id]
    >>> browser.getControl(name=id+'.outcome').value = ['pass']
    >>> form.submit('Apply')

    >>> print browser.contents
    <BLANKLINE>
    ...
    <div id="message">Student processes successfully updated.</div>
    ...
    <tr>
      <td>
        <input type="checkbox" name="ids:list"
               value="srichter" />
      </td>
      <td>
        <span>Stephan Richter</span>
        (<span>srichter</span>)
      </td>
    </tr>
    ...

That's it. We have successfully moved through a student's academic career.


And a second time ...
---------------------

Let's now do this again in a student-specific UI. To make the walkthrough
cleaner, we create a new student first:

    >>> browser.getLink('Persons').click()
    >>> browser.getLink('New Person').click()

    >>> browser.getControl('Full name').value = 'Tom Hoffman'
    >>> browser.getControl('Username').value = 'tom'
    >>> browser.getControl('Password').value = 'foobar'
    >>> browser.getControl('Verify password').value = 'foobar'
    >>> browser.getControl('Photo').value = StringIO.StringIO()
    >>> browser.getControl('Add').click()

    >>> print browser.contents
    <BLANKLINE>
    ...
    <a href="http://localhost/persons/tom">Tom Hoffman</a>
    ...

Now we enter the new student and look at his academic career:

    >>> browser.getLink('Tom Hoffman').click()
    >>> browser.getLink('Academic Record').click()

In the academic record you see the status of the student, the workflow and the
academic history:

    >>> print browser.contents
    <BLANKLINE>
    ...
    <h1>
      Academic Record for <em>Tom Hoffman</em>
    </h1>
    ...
    <h3>Status</h3>
    ...
    <h3>Workflow</h3>
    ...
    value="Initialize"
    ...
    <h3>History</h3>
    <ul style="list-style: disc">
    </ul>
    ...

We can see that there is currently no workflow and the history is empty. Let's
now create the workflow:

    >>> browser.getControl('Initialize').click()

    >>> print browser.contents
    <BLANKLINE>
    ...
    <div id="message">The Level Process was successfully initialized.</div>
    ...
    <h5>Select Initial Level</h5>
    ...
    <h3>History</h3>
    <ul style="list-style: disc">
      <li>
        <em>Enrolled</em>
        <div style="font-size: smaller">
           on <span>...</span>
           by <span>sb.person.manager</span>
        </div>
        <p>Enrolled at school</p>
      </li>
    </ul>
    ...

You see that we can now specify the initial level of the student and a history
entry was added signalizing the beginning of the student's academic
career. Let's now select the initial level:

    >>> id = browser.getControl(name='workitemId').value
    >>> browser.getControl(name=id+'.level').value = ['level1']
    >>> browser.getControl('Finish').click()

    >>> print browser.contents
    <BLANKLINE>
    ...
    <div id="message">Work Item successfully finished.</div>
    ...
    <h5>Set Level Outcome</h5>
    ...
    <p>Current Level: 1st Grade</p>
    ...

Now let's fail the student in the first grade:

    >>> id = browser.getControl(name='workitemId').value
    >>> browser.getControl(name=id+'.outcome').value = ['fail']
    >>> browser.getControl('Finish').click()

    >>> print browser.contents
    <BLANKLINE>
    ...
    <div id="message">Work Item successfully finished.</div>
    ...
    <h5>Set Level Outcome</h5>
    ...
    <h3>History</h3>
    <ul style="list-style: disc">
    ...
      <li>
        <em>Failed</em>
        <div style="font-size: smaller">
           on <span>...</span>
           by <span>sb.person.manager</span>
        </div>
        <p>Failed level "1st Grade"</p>
      </li>
    </ul>
    ...

After the first grade, the student withdraws from the school:

    >>> id = browser.getControl(name='workitemId').value
    >>> browser.getControl(name=id+'.outcome').value = ['withdraw']
    >>> browser.getControl('Finish').click()

    >>> print browser.contents
    <BLANKLINE>
    ...
    <h3>Workflow</h3>
    <div id="message">Work Item successfully finished.</div>
    ...
    value="Initialize"
    ...
    <h3>History</h3>
    <ul style="list-style: disc">
    ...
      <li>
        <em>Withdrawn</em>
        <div style="font-size: smaller">
           on <span>...</span>
           by <span>sb.person.manager</span>
        </div>
        <p>Withdrew before or during level "1st Grade"</p>
      </li>
    </ul>
    ...

As you can see, the withdrawing from the school also removed the process.

To get the correct status, we first have to reload:

    >>> browser.reload()
    >>> print browser.contents
    <BLANKLINE>
    ...
    <h3>Status</h3>
    ...
    <option selected="selected" value="Withdrawn">Withdrawn</option>
    ...

One very powerful feature of the academic record screen is the removal of a
workflow:

    >>> browser.getControl('Initialize').click()
    >>> browser.getControl('Remove').click()

    >>> print browser.contents
    <BLANKLINE>
    ...
    <h3>Workflow</h3>
    <div id="message">The Level Process was successfully removed.</div>
    ...
    value="Initialize"
    ...

We just need to make sure that all the workitems got deleted as well:

    >>> browser.getLink('Groups').click()
    >>> browser.getLink('Manager', url='groups/manager').click()
    >>> browser.getLink('Student Management').click()

    >>> print browser.contents
    <BLANKLINE>
    ...
    <h3>Initialize Students</h3>
    ...
    <table width="100%">
      <tr>
        <th width="5%">&nbsp;</th>
        <th width="45%">Student Name (username)</th>
        <th width="50%">Inital Level</th>
      </tr>
    </table>
    ...

That's all.
