"""
Calendaring for Zope 3 applications.

SchoolBell is a calendaring library for Zope 3.  Its main features are
(currently most of these features are science fiction):

- It can parse and generate iCalendar files.  Only a subset of the iCalendar
  spec is supported, however it is a sensible subset that should be enough for
  interoperation with desktop calendaring applications like Apple's iCal,
  Mozilla Calendar, Evolution, and KOrganizer.

- It has browser views for presenting calendars in various ways (daily, weekly,
  monthly, yearly views).

- It is storage independent -- your application could store the calendar in
  ZODB, in a relational database, or elsewhere, as long as the storage
  component provides the necessary interface.  A default content component
  that stores data in ZODB is provided.

- You can also generate calendars on the fly from other data (e.g. a bug
  tracking system).  These calendars can be read-only (simpler) or read-write.

- You can display several calendars in a single view by using calendar
  composition.

- It supports recurring events (daily, weekly, monthly and yearly).

Things that are not currently supported:

- Timezone handling (UTC times are converted into server's local time in the
  iCalendar parser, but that's all).

- All-day events (that is, events that only specify the date but not the time).

- Informing the user when uploaded iCalendar files use features that are not
  supported by SchoolBell.

"""
