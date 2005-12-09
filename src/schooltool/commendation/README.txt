========================================
The Commendation Package (Documentation)
========================================

The prime purpose of this package is to document the implementation of an
additional content component in SchoolTool. To motivate the documentation, Tom
Hoffman, the SchoolTool project manager, will act as the customer for this
extension, and the protagonist of the writing is the developer fulfilling the
customer's specifications.

Here is the original E-mail that contains Tom's specifications:

  I think for our sample product documentation, the opposite of our
  discipline referral system might be simple enough, that is, a
  commendation system (since no workflow is necessary).

  The overall idea is to allow teachers, clerks and administrators to
  enter a commendation for a person or group (including sections).

  Commendations are, by definition, public.

  Commendations have the following fields:

   * Scope: [group, school-wide, community, state, national, global]
   * Grantor
   * Title
   * Description
   * Date

  Users with the proper role should have an "Add commendation" action
  when they're viewing a person or group.

  If a user or group has a commendation, a "View commendations" action
  should be visible.

  For the school, a "View commendations" action should present a
  batched/searchable list of all commendations in reverse chronological
  order.

Thus, this documentation package will implement a simple commendation
system. To make the documentation more readible, it is split into four
sections as outlined below.


Outline
-------

1. Development of the ``Commendation`` Component

   [``BasicComponent.txt``]

   (a) Creating the Package
   (b) Development of the ``ICommendation`` Interface
   (c) Implementation of the ``Commendation`` Component
   (d) Testing the Implementation

2. Python-Integration of Commendations into SchoolTool

   [``PythonIntegration.txt``]

   (a) The ``Commendations`` container
   (b) Asoociating Commendations with SchoolTool Components

3. System-Integration of Commentations into SchoolTool

   [``SystemIntegration.txt``]

   (a) ZCML Registration of new Components
   (b) Create an Add and Edit View
   (c) Setup correct Security

4. Viewing the Commendations

   [``Viewing.txt``]

   (a) Commendations View for SchoolTool Components
   (b) Commendations Viewlet
   (c) School-wise Commendations Overview
