
================
Testing workflow
================

:Authors:
    Fabian Deutsch <fabiand@fedoraproject.org>


Overview
--------

Igor is preparing a host with a profile.
When the host finally starts up, a client script - that is expected to be run
by the host - is executed and fetches a **testsuite**.

The downloaded **testsuite** is a bzipped tarball which contains all testcases
and maybe some libraries (if they were specified in a **testset**).

All testcases in the downloaded testsuite are prefixed with a number, this
defines the order among the testcases.
For example::

    1-finish_installation.sh
    2-set_admin_password.sh
    …

Now all testcases are run - so executed - one after another.
A testcase can be a bash or python script, or any other executable that can be
run on the host.


Reboot
------

It is essential that the host can be rebooted during the test process. To allow
this, igor is keeping track (on the server side) at what step a host was.
This enables the host to continue the testsuite at the correct testcase.



