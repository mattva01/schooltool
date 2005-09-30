Functional tests for SchoolTool Level RESTive views
===================================================

Level Managament
----------------

We need the REST HTTP caller:

    >>> from schooltool.app.rest.ftests import rest

Initially, we have no levels.

    >>> print rest("""
    ... GET /levels/ HTTP/1.1
    ... Authorization: Basic manager:schooltool
    ... """)
    HTTP/1.1 200 Ok
    ...
    <container xmlns:xlink="http://www.w3.org/1999/xlink">
      <name>levels</name>
      <items>
      </items>
      <acl xlink:type="simple" xlink:title="ACL"
           xlink:href="http://localhost/levels/acl"/>
    </container>
    <BLANKLINE>

Let's now create two levels:

    >>> print rest("""
    ... PUT /levels/level2 HTTP/1.1
    ... Authorization: Basic manager:schooltool
    ... Content-Type: text/xml
    ...
    ... <object xmlns="http://schooltool.org/ns/model/0.1"
    ...         title="2nd Grade" isInitial="false" />
    ... """)
    HTTP/1.1 201 Created
    ...

    >>> level2 = getRootFolder()['levels']['level2']
    >>> level2
    <Level '2nd Grade'>

    >>> print rest("""
    ... PUT /levels/level1 HTTP/1.1
    ... Authorization: Basic manager:schooltool
    ... Content-Type: text/xml
    ...
    ... <object xmlns="http://schooltool.org/ns/model/0.1"
    ...         title="1st Grade" isInitial="true" nextLevel="level2" />
    ... """)
    HTTP/1.1 201 Created
    ...

    >>> level1 = getRootFolder()['levels']['level1']
    >>> level1
    <Level '1st Grade'>
    >>> level1.nextLevel is level2
    True

Let's see what a level looks like:

    >>> print rest("""
    ... GET /levels/level1 HTTP/1.1
    ... Authorization: Basic manager:schooltool
    ... """)
    HTTP/1.1 200 Ok
    Content-Length: ...
    Content-Type: text/xml; charset=UTF-8
    Set-Cookie: ...
    <BLANKLINE>
    <level xmlns:xlink="http://www.w3.org/1999/xlink">
      <title>1st Grade</title>
      <isInitial>true</isInitial>
      <nextLevel>level2</nextLevel>
      <relationships xlink:type="simple"
                     xlink:title="Relationships"
                     xlink:href="http://localhost/levels/level1/relationships"/>
      <acl xlink:type="simple" xlink:title="ACL"
           xlink:href="http://localhost/levels/level1/acl"/>
    </level>
    <BLANKLINE>


Academic Record of a Student
----------------------------

We first have to create a student for which we observe the academic record:

    >>> print rest("""
    ... PUT /persons/stephan HTTP/1.1
    ... Authorization: Basic manager:schooltool
    ... Content-Type: text/xml
    ...
    ... <object xmlns="http://schooltool.org/ns/model/0.1" title="Stephan"/>
    ... """)
    HTTP/1.1 201 Created
    ...


Let's first look at the academic status. You can simply get it and put it:

    >>> print rest("""
    ... GET /persons/stephan/academicStatus HTTP/1.1
    ... Authorization: Basic manager:schooltool
    ... """)
    HTTP/1.1 200 Ok
    Content-Length: 0
    Content-Type: text/plain
    Set-Cookie: ...
    <BLANKLINE>

    >>> print rest("""
    ... POST /persons/stephan/academicStatus HTTP/1.1
    ... Authorization: Basic manager:schooltool
    ... Content-Type: text/xml
    ...
    ... Enrolled
    ... """)
    HTTP/1.1 200 Ok
    ...

    >>> print rest("""
    ... GET /persons/stephan/academicStatus HTTP/1.1
    ... Authorization: Basic manager:schooltool
    ... """)
    HTTP/1.1 200 Ok
    Content-Length: 8
    Content-Type: text/plain
    Set-Cookie: ...
    <BLANKLINE>
    Enrolled


Now let's create a promotion workflow At the beginning there is nothing:

    >>> print rest("""
    ... GET /persons/stephan/promotion HTTP/1.1
    ... Authorization: Basic manager:schooltool
    ... """)
    HTTP/1.1 200 Ok
    ...

You can create one by putting it there.

    >>> print rest("""
    ... PUT /persons/stephan/promotion HTTP/1.1
    ... Authorization: Basic manager:schooltool
    ... """)
    HTTP/1.1 200 Ok
    ...

If we now look at the promotion again, we will see that it now returns a
workflow item.

    >>> print rest("""
    ... GET /persons/stephan/promotion HTTP/1.1
    ... Authorization: Basic manager:schooltool
    ... """)
    HTTP/1.1 200 Ok
    Content-Length: 55
    Content-Type: text/xml; charset=UTF-8
    Set-Cookie: ...
    <BLANKLINE>
    <setinitiallevel>
      <initialLevel/>
    </setinitiallevel>
    <BLANKLINE>

Now we set the initial level:

    >>> print rest("""
    ... POST /persons/stephan/promotion HTTP/1.1
    ... Authorization: Basic manager:schooltool
    ... Content-Type: text/xml
    ...
    ... <object xmlns="http://schooltool.org/ns/model/0.1"
    ...         initialLevel="level1" />
    ... """)
    HTTP/1.1 200 Ok
    Content-Length: ...
    Set-Cookie: ...
    <BLANKLINE>
    Initial Level selected.

We can see that the next action must be setting the outcome of the first
grade:

    >>> print rest("""
    ... GET /persons/stephan/promotion HTTP/1.1
    ... Authorization: Basic manager:schooltool
    ... """)
    HTTP/1.1 200 Ok
    Content-Length: ...
    Content-Type: text/xml; charset=UTF-8
    Set-Cookie: ...
    <BLANKLINE>
    <setleveloutcome>
      <level>level1</level>
      <outcome/>
    </setleveloutcome>
    <BLANKLINE>

    >>> print rest("""
    ... POST /persons/stephan/promotion HTTP/1.1
    ... Authorization: Basic manager:schooltool
    ... Content-Type: text/xml
    ...
    ... <object xmlns="http://schooltool.org/ns/model/0.1"
    ...         outcome="pass" />
    ... """, handle_errors=False)
    HTTP/1.1 200 Ok
    Content-Length: ...
    Set-Cookie: ...
    <BLANKLINE>
    Outcome submitted.

Also pass the second grade:

    >>> print rest("""
    ... GET /persons/stephan/promotion HTTP/1.1
    ... Authorization: Basic manager:schooltool
    ... """)
    HTTP/1.1 200 Ok
    Content-Length: ...
    Content-Type: text/xml; charset=UTF-8
    Set-Cookie: ...
    <BLANKLINE>
    <setleveloutcome>
      <level>level2</level>
      <outcome/>
    </setleveloutcome>
    <BLANKLINE>

    >>> print rest("""
    ... POST /persons/stephan/promotion HTTP/1.1
    ... Authorization: Basic manager:schooltool
    ... Content-Type: text/xml
    ...
    ... <object xmlns="http://schooltool.org/ns/model/0.1"
    ...         outcome="pass" />
    ... """, handle_errors=False)
    HTTP/1.1 200 Ok
    Content-Length: ...
    Set-Cookie: ...
    <BLANKLINE>
    Outcome submitted.

Now the promotion process is done and the promotion obejct is empty again:

    >>> print rest("""
    ... GET /persons/stephan/promotion HTTP/1.1
    ... Authorization: Basic manager:schooltool
    ... """)
    HTTP/1.1 200 Ok
    Content-Length: 0
    Content-Type: text/plain
    Set-Cookie: ...
    <BLANKLINE>

Now that the workflow is done, we can look at the academic history of the
student:

    >>> print rest("""
    ... GET /persons/stephan/academicHistory HTTP/1.1
    ... Authorization: Basic manager:schooltool
    ... """)
    HTTP/1.1 200 Ok
    Content-Length: ...
    Content-Type: text/xml; charset=UTF-8
    Set-Cookie: ...
    <BLANKLINE>
    <history>
      <entry>
        <title>Enrolled</title>
        <description>Enrolled at school</description>
        <timestamp>...</timestamp>
      </entry>
      <entry>
        <title>Passed</title>
        <description>Passed level "1st Grade"</description>
        <timestamp>...</timestamp>
      </entry>
      <entry>
        <title>Passed</title>
        <description>Passed level "2nd Grade"</description>
        <timestamp>...</timestamp>
      </entry>
    </history>
    <BLANKLINE>
