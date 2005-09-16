Safety net for unit tests
=========================

This directory contains an optional safety net for unit tests.  The 'checks.py'
module contains a number of checkers, each of which ensures that all unit tests
properly implement some particular aspect (such as cleaning up a global
registry, or printing random debugging stuff to stdout).

