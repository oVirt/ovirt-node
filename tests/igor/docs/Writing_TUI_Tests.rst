
====================================
Writing TUI tests using common.input
====================================

:Authors:
    Fabian Deutsch <fabiand@fedoraproject.org>


What is needed
--------------
common.input is a convenience python library for testing the oVirt Node TUI (or
any other console/terminal based interaction).

How to use it
-------------

The high level object ``common.input.Storyboard`` provides everything you need.
Typically you specify a story like::

  story = [
    (None,  0,  "login:"),
    ("root\n",    1,  "Password:"),
    ("masterpw\n",  0, None)
  ]

This can be read as:

1. In the beginning (``None, 0``) expect a ``login:`` text somewhere on the
screen.
2. If so, type ``root\n``, ``\n`` get's translated to ``<ENTER>``, so
simulating the Enter-Key being stroked) and expect ``Password:`` to appear
somewhere on the screen.

And so on.

This ``story`` is passed to an Storyboard object and can be run afterwards::

    storyboard = common.input.Storyboard("some title", story)
    storyboard.run_and_exit()

``run_and_exit()`` is running the story and checks if it behaves like described
in the story.
The ``run_and_exit`` returns
- 0 (interpreted as **passed**) if the story behaves as expected or
- 1 (interpreted as **failed**) if it does *not* behave as expected.
