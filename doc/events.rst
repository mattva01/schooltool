Events
======

Overview
--------

The event system is an important part of schooltool. Configuring the route
events take around the system, and what objects take action based on events,
is how we represent the way that information and the need for action is
communicated in real life.

The event system can be configured in a wide variety of ways. Event policy
can be set on an individual object (for example, a particular Pupil needs
to have absences particularly noted), or collectively on behalf of groups
of objects. (For example, all teachers who are class tutors need to note
when pupils are absent for several consecutive registrations.)

XXX: talk about facets, relationships and events.

XXX: Mention Zope3 events, adapter-based subscriptions.

See code
--------

In src/schooltool/interface.py
  IEvent
  IEventTarget
  IEventService
  IEventConfigurable
  IEventAction
  ILookupAction
  IRouteToMembersAction
  IRouteToGroupsAction


Glossary
--------

:Event target:
  An object that can receive an event. An event target is "notified" of an
  event.

:Subscription:
  The act of subscribing to the event service. Also, an 
  (event target, event type) tuple that represents a subscription.

:Service:
  One of a number of global singleton objects that provide a central
  point for various services. Examples include the event service and
  the error logging service.

:Event service:
  A service that is notified of each event sent in the system.
  Objects that are event targets can subscribe to the event service to
  receive particular types of event.

:Event:
  A packet of information sent to event targets.

  Events are classified in a hierarchy (actually, an acyclic directed graph,
  like a python class hierarchy). An event ensures that a particular
  event target receives it just once.

  Sending an event to an event target is called "dispatching" the event.
  An event ensures that it has been dispatched to the event service
  before it is despatched to any other event targets.

  An event carries a payload. An event's type and its payload reflects the
  purpose of the event. For example, we might decide that an AbsenteeEvent
  is a type of PupilRegistrationEvent. An PupilRegistrationEvent carries
  a Pupil object and a Registration object as payload. A Registration object
  represents the presence or absense of a Pupil at a given registration
  session on a particular date.
  So, the payload for an AbsenteeEvent is the same as that of a
  PupilRegistrationEvent.

:Error logging service:
  An example of a service that records unhandled errors for inspection later.
  This has nothing in particular to do with events.

:Event table:
  A list of event actions that is managed by an object that handles events
  in a configurable way.
  For a group or person in schooltool, the event table is an amalgamation
  of the event tables of the group or person's facets_, and its user-editable
  event table.

:Event action:
  A particular action to be taken on receipt of a particular type of event.
  For example, a pupil on receiving an AbsenteeEvent can be configured with
  a RouteToRelationship action that sends the event to the pupil's parents or
  legal guardians.

  Typical actions are

  * route to the members of this group

  * route to the groups this object is a member of

  * route via all relationships of type 'legal guardian'

  * handle the event in the "registration class tutor" facet of this person

  See also groups_.


Typical example
---------------

XXX: talk about absence event being triggered for a pupil, being collected
     by the RegistrationProcess, late pupils being removed from the list,
     pupils still absent after 1 hour of lateness being followed up.
     All being inspectible over REST HTTP.


.. _facets: See facets.rst

.. _groups: See groups.rst
