=====================================================
Level Management and Academic Workflow via the Web UI
=====================================================

This document presents the management of levels and the academic career of a
student via a promotion workflow from the perspective of the Web UI.

  >>> from zc.mechtest.testing import Browser
  >>> browser = Browser()
  >>> browser.addHeader('Authorization', 'Basic mgr:mgrpw')

  >>> browser.open(
  ...     'http://localhost/contents.html?'
  ...     'type_name=BrowserAdd__schooltool.app.SchoolToolApplication&'
  ...     'new_value=test')

  >>> "test" in browser.contents
  True
  >>> browser.click('test')


Level Management
----------------

First we create a couple of levels.

  >>> browser.click('Levels')

  >>> browser.click('New Level')
  >>> browser.controls['field.title'] = u'1st Grade'
  >>> browser.controls['field.isInitial'] = True
  >>> browser.controls['add_input_name'] = u'level1'
  >>> browser.click('Add')

  >>> '1st Grade' in browser.contents
  True

  >>> browser.click('New Level')
  >>> browser.controls['field.title'] = u'2nd Grade'
  >>> browser.controls['field.isInitial'] = False
  >>> browser.controls['add_input_name'] = u'level2'
  >>> browser.click('Add')

  >>> '2nd Grade' in browser.contents
  True

Since we did not connect the two levels, validation should fail:

  >>> browser.click('Validate Levels')
  >>> browser.click('Validate')

  >>> "One or more disconnected levels detected." in browser.contents
  True
  >>> "2nd Grade" in browser.contents
  True

If we connect `level1` to `level2` and also `level2` to `level1`, we get a
loop validation error:

  >>> browser.click('Levels')
  >>> browser.click('1st Grade')
  >>> browser.click('Edit Info')
  >>> browser.controls['field.nextLevel'] = ['level2']
  >>> browser.click('Apply')

  >>> browser.click('Levels')
  >>> browser.click('2nd Grade')
  >>> browser.click('Edit Info')
  >>> browser.controls['field.nextLevel'] = ['level1']
  >>> browser.click('Apply')
  
  >>> browser.click('Levels')
  >>> browser.click('Validate Levels')
  >>> browser.click('Validate')

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

  >>> browser.click('Levels')
  >>> browser.click('2nd Grade')
  >>> browser.click('Edit Info')
  >>> browser.controls['field.nextLevel'] = []
  >>> browser.click('Apply')

  >>> browser.click('Levels')
  >>> browser.click('Validate Levels')
  >>> browser.click('Validate')

  >>> print browser.contents
  <BLANKLINE>
  ...
  No errors were detected.
  ...


The Academic Career of a Student
--------------------------------

Before we can do anything, we have to create a student:

  >>> import StringIO

  >>> browser.click('Persons')
  >>> browser.click('New Person')

  >>> browser.controls['field.title'] = 'Stephan Richter'
  >>> browser.controls['field.username'] = 'srichter'
  >>> browser.controls['field.password'] = 'foobar'
  >>> browser.controls['field.verify_password'] = 'foobar'
  >>> browser.controls['field.photo'] = StringIO.StringIO()
  >>> browser.click('Add')

  >>> 'Stephan Richter' in browser.contents
  True

Now we go to the manager group, and walk the student through the academic
career:

  >>> browser.click('Groups')
  >>> browser.click('Manager')
  >>> browser.click('Student Management')

We now select the student which we want to enroll in the school.

  >>> form = browser.forms['enroll']
  >>> ctrl = browser.getControl('ids:list', form=form.mech_form) 
  >>> ctrl.mech_control.value = ['srichter']
  >>> browser.click('Enroll')

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

  >>> form = browser.forms['initialize']
  >>> ctrl = browser.getControl('ids:list', form=form.mech_form) 
  >>> id = ctrl.options[0]
  >>> ctrl.mech_control.value = [id]
  >>> browser.controls[id+'.level'] = ['level1']
  >>> browser.click('Apply')

  >>> print browser.contents
  <BLANKLINE>
  ...
  <div id="message">Student processes successfully updated.</div>
  ...
  <div class="value">
  <select name="...outcome" size="1" >
  <option selected="selected" value="pass">pass</option>
  <option value="fail">fail</option>
  <option value="withdraw">withdraw</option>
  </select>
  </div>
  ...

The student passes the first grade

  >>> form = browser.forms['outcome']
  >>> ctrl = browser.getControl('ids:list', form=form.mech_form) 
  >>> id = ctrl.options[0]
  >>> ctrl.mech_control.value = [id]
  >>> browser.controls[id+'.outcome'] = ['pass']
  >>> form.submit('Apply')

  >>> print browser.contents
  <BLANKLINE>
  ...
  <div id="message">Student processes successfully updated.</div>
  ...
  <span>2nd Grade</span>
  ...
  
but fails the second grade the first time around:

  >>> form = browser.forms['outcome']
  >>> ctrl = browser.getControl('ids:list', form=form.mech_form) 
  >>> id = ctrl.options[0]
  >>> ctrl.mech_control.value = [id]
  >>> browser.controls[id+'.outcome'] = ['fail']
  >>> form.submit('Apply')

  >>> print browser.contents
  <BLANKLINE>
  ...
  <div id="message">Student processes successfully updated.</div>
  ...
  <span>2nd Grade</span>
  ...

If you forget to select the student, you get a nice notice:

  >>> form = browser.forms['outcome']
  >>> ctrl = browser.getControl('ids:list', form=form.mech_form) 
  >>> id = ctrl.options[0]
  >>> browser.controls[id+'.outcome'] = ['fail']
  >>> form.submit('Apply')

  >>> print browser.contents
  <BLANKLINE>
  ...
  <div id="message">No students were selected.</div>
  ...

Now we finally pass the student, so he will graduate; that means he will
appear at the top of the list again:

  >>> form = browser.forms['outcome']
  >>> ctrl = browser.getControl('ids:list', form=form.mech_form) 
  >>> id = ctrl.options[0]
  >>> ctrl.mech_control.value = [id]
  >>> browser.controls[id+'.outcome'] = ['pass']
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

  >>> browser.click('Persons')
  >>> browser.click('New Person')

  >>> browser.controls['field.title'] = 'Tom Hoffman'
  >>> browser.controls['field.username'] = 'tom'
  >>> browser.controls['field.password'] = 'foobar'
  >>> browser.controls['field.verify_password'] = 'foobar'
  >>> browser.controls['field.photo'] = StringIO.StringIO()
  >>> browser.click('Add')

  >>> print browser.contents
  <BLANKLINE>
  ...
  <a href="http://localhost/test/persons/tom">Tom Hoffman</a>
  ...

Now we enter the new student and look at his academic career:

  >>> browser.click('Tom Hoffman')
  >>> browser.click('Academic Record')

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

  >>> browser.click('Initialize')
 
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
         by <span>zope.mgr</span>
      </div>
      <p>Enrolled at school</p>
    </li>
  </ul>
  ...

You see that we can now specify the initial level of the student and a history
entry was added signalizing the beginning of the student's academic
career. Let's now select the initial level:

  >>> id = browser.controls['workitemId']
  >>> browser.controls[id+'.level'] = ['level1']
  >>> browser.click('Finish')

  >>> print browser.contents
  <BLANKLINE>
  ...
  <div id="message">Work Item successfully finished.</div>
  ...
  <h5>Set Level Outcome</h5>
  ...

Now let's fail the student in the first grade:

  >>> id = browser.controls['workitemId']
  >>> browser.controls[id+'.outcome'] = ['fail']
  >>> browser.click('Finish')

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
         by <span>zope.mgr</span>
      </div>
      <p>Failed level "1st Grade"</p>
    </li>
  </ul>
  ...

After the first grade, the student withdraws from the school:

  >>> id = browser.controls['workitemId']
  >>> browser.controls[id+'.outcome'] = ['withdraw']
  >>> browser.click('Finish')

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
         by <span>zope.mgr</span>
      </div>
      <p>Withdrew before or during level "1st Grade"</p>
    </li>
  </ul>
  ...

As you can see, the withdrawing from the school also removed the process.

To get the correct status,w e first have to reload:

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

  >>> browser.click('Initialize')
  >>> browser.click('Remove')

  >>> print browser.contents
  <BLANKLINE>
  ...
  <h3>Workflow</h3>
  <div id="message">The Level Process was successfully removed.</div>
  ...
  value="Initialize"
  ...

We just need to make sure that all the workitems got deleted as well:

  >>> browser.click('Groups')
  >>> browser.click('Manager')
  >>> browser.click('Student Management')

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