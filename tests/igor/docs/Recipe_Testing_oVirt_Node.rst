
===========================================
Setting Up Automatedt Testing of oVirt Node
===========================================

:Authors:
    Fabian Deutsch <fabiand@fedoraproject.org>

.. _Intention:

Intention
--------------------------------------------------------------------------------

Enable running fully automated tests on a Node instance using four lines::

    # IMPORTANT: Add the client to the ISO
    sudo $NODE_BASE/tools/edit-node \
        --install=ovirt-autotesting-systemd \
        --repo autotesting.repo \
        --nogpgcheck ~/Downloads/ovirt-node-iso-2.5.0-1.0.fc17.iso

    # Open a firewall port to allow clients to connect to igor
    sudo lokkit --port=8080:tcp

    # Submit the ISO to be run against a testplan
    sudo $IGOR_BASE/igor/data/igorclient.sh \
        run_testplan_on_iso mi_ai_extended \
        ~/Downloads/ovirt-node-iso-2.5.0-1.0.fc17.iso.edited.iso \
        "local_boot_trigger=$IGOR_HOST:8080/testjob/{igor_cookie}"

    # Open the UI to track the progress:
    xdg-open http://127.0.0.1:8080/



Ingredients
--------------------------------------------------------------------------------
- oVirt Node Image - The image to be tested
  http://ovirt.org/releases/stable/binary/
- oVirt Node Source - Provides the edit-node tool and testsuites
- Igor- Is the logic and creates and provisions VMs on demand and runs tests
- libvirt - For hosting and controlling VMs (used for testing Node)
- Cobbler - For provisioning the hosts



Recipe
--------------------------------------------------------------------------------

Overview
~~~~~~~~
Igor is taking testsuites - part of oVirt Node's sources - and runs them on
hosts (in this case VM's handled by libvirt).
The host is set up using an oVirt Node image (e.g. a stable, nightly, or your
custom build) and cobbler, which is used for provisioning the host.

Shortcut
~~~~~~~~
- Setup cobbler with managed tftp
- Setup libvirt with a bootp entry pointing to cobbler server
- Exchange ssh keys to allow the user which igor is runnig as to connect to
  root@cobbler server
- Checkout igor sources
- Edit igord.cfg (update at least testcases/path, Testplans/path,
  cobbler/ssh_uri, libvirtd/connection_uri)
- Open UI http://localhost:8080
- Submit jobs as described in Intention_


Set up Cobbler
~~~~~~~~~~~~~~
Cobbler is a key component, and is used to offer tftp and dhcp to the clients.
- Install Fedora 16
- Install cobbler
- Enable tftp

On the cobbler server ensure to run::

    $ cobbler check

To ensure that cobbler is running fine.


Set up libvirt
~~~~~~~~~~~~~~
On the cobbler host, or a different e.g. Fedora host:
- yum groupinstall virtualization
- systemctl enable libvirt.service

Now edit the default network config to point clients to cobbler's tftp server::

    $ virsh net-edit default

Add the following line into the ``dhcp`` element of the definition::

    <bootp file='/pxelinux.0' server='192.168.122.33' />

You have to restart the ``default`` network so your changes have an effect::

    $ virsh net-destroy default       # Stop
    $ virsh net-start default         # Start


Checking out ovirt-node
~~~~~~~~~~~~~~~~~~~~~~~
The oVirt Node sources are required because they provide the testcases and the
``edit-node`` tool, which is required later on::

    $ cd $NODE_BASE
    $ git clone git://gerrit.ovirt.org/ovirt-node


Exchanging relevant ssh keys
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Igor needs to push files (kernel, initrd) to the cobbler server. This is done
via ssh/scp.
Igor needs access to cobbler, therefor, on the machine and as the user that is
going to run igor::

    $ ssh-keygen
    $ ssh-copy-id root@$COBBLER_HOST


Setting up Igor
~~~~~~~~~~~~~~~
Igor is configured through the ``igord.cfg`` configuraion file. An example of
this file is kept in the ``data/`` subfolder.
Copy the example into igor's toplevel dir and edit it::

    $ cd $IGOR_BASE
    $ git clone git://gitorious.org/ovirt/igord.git
    $ cp data/igord.cfg.example igord.cfg
    $ edit igord.cfg

Update the sections according to the notes below ([Section]/[Variable])

Testcases/path
    This is the path where the testsuites reside, igor reads this suites and
    loads the reference testsets and testcases.
    Set this to: $NODE_BASE/tests/igor/suites (remember to replace $NODE_BASE)

Testplans/path
    Plans are handled somewhat differently therefor a second path needs to be
    set. Set this to: $NODE_BASE/tests/igor/plans (remember to replace
    $NODE_BASE)

Hosts/path
     this as it is.

Session/path
    Igor creates some temporary files (like artifacts).
    You can use e.g. ``/srv/igord`` for this.

Cobbler/username and password
    The ``username`` and ``password`` used to authenticate with the cobbler
    server we configured above.
    Cobbler's debug mode is using cobbler/cobbler.

Cobbler/ssh_uri
    This is ssh uri used to connect to the host where your cobbler server is
    running on.

Cobbler.Hosts/identification_expression
    If a cobbler hostname is prefixed with this expression, the Igor will allow
    to use this host for testing.

Cobbler.Host/Whitelist
    This file contains one hostname per line that should be allowed to be used
    for testing.

libvirtd/connection_uri
    This URI is used by Igor to create VMs. You can use the URI to point Igor
    to any local or remote libvirt instance.
    ``qemu:///system`` points to a local instance, have a look at libvirt's
    documentation for more examples.

libvirtd.virt-install/storage_pool and network_configuration
    These two parameters are passed to virt_install when new domain definitions
    are created, the default values should match libvirts defaults.
    Refere to virt-install's documentation for more examples.

Run igord
~~~~~~~~~
After we've configured everything run igord::

    cd $IGOR_BASE
    reset
    sudo PYTHONPATH=. nice python bin/igord

Igor also has a UI which can now be viewed by pointing your browser to
http://localhost:8080 .

The igorclient
~~~~~~~~~~~~~~
A running igor instance can be controlled using the ``igorclient.sh`` which is
residing in ``$IGOR_BASE/igor/data``.

To get an overview over all available commands just run::

    $ cd $IGOR_BASE/igor/data/
    $ ./igorclient.sh

Details to a specififc command which expects parameters can displayed if the
command is run without any parameter::

    $ ./igor/data/igorclient.sh submit
    Testsuitename is mandatory.
    Usage: ./igor/data/igorclient.sh submit <TESTSUITE> <PROFILE> <HOST> 
    [<KARGS>]

Normally the client contains commands for all functions which are provided by
igord's (rest-like) API.

Testing an oVirt Node ISO
'''''''''''''''''''''''''
The most easiest way is now to use the function ``run_testplan_on_iso`` which
runs the specified testplan on the given ISO::

    # IMPORTANT: Add the client to the ISO
    sudo $NODE_BASE/tools/edit-node \
        --install=ovirt-autotesting-systemd \
        --repo autotesting.repo \
        --nogpgcheck ~/Downloads/ovirt-node-iso-2.5.0-1.0.fc17.iso

    # Open a firewall port to allow clients to connect to igor
    sudo lokkit --port=8080:tcp

    # Submit the ISO to be run against a testplan
    sudo $IGOR_BASE/igor/data/igorclient.sh \
        run_testplan_on_iso mi_ai_extended \
        ~/Downloads/ovirt-node-iso-2.5.0-1.0.fc17.iso.edited.iso \
        "local_boot_trigger=$IGOR_HOST:8080/testjob/{igor_cookie}"

    # Open the UI to track the progress:
    xdg-open http://127.0.0.1:8080/

The ``run_testplan_on_iso`` command will extract the kernel, initrd and default
kargs which are used to boot the kernel from the ISO and upload them to igord
using the ``add_profile_from_iso`` command (which you can also use). Afterwards
``testplan_submit`` is used to initiate a testplan run using new previosuly
created profile. After waiting for the testplan to finish ``remove_profile``
is used to remove te profile which was created in the beginning (from the ISO).

This is the most high-level convenience function an is recommended to be used
to test new Node ISOs.

Another word regarding the client - the oVir Node Igor Client is kept in an
extra repository. The client is _not_, understand as _not_, part of any official
oVirt Node build because it is a _major_ security hole, as it executes arbitary
code on an installed oVirt Node.
Therefor you need to `edit` - install the client into the ISO - each ISO you
want to test, using the node-edit tool provided by oVirt Node (in the ``tools/``
subdirectory) sources.

Viewing the source of commands
''''''''''''''''''''''''''''''
You can also view what how the `run_testplan_on_iso`` does by running::

    $ $IGOR_BASE/igor/data/igorclient.sh view run_testplan_on_iso

This works for all commands.

Profiles and how to use them
''''''''''''''''''''''''''''
A profile consists of a kernel (vmlinuz), initramfs (initrd) files and a third
file containing the arguments passed to the kernel (kargs).

Profiles known by igor (and which can therefor be used with tests) can be viewed
using the ``profiles`` command.

There are several ways to create a profile:

* ``add_profile`` adds a new profile using given kernel, initrd and kargs files
* ``add_profile_from_iso`` adds a new profile using a iven LiveCD and extracting
  the kernel, initrd and kargs and subsequently calling ``add_profile`` with
  these files.
* ``remove_profile`` can be used to remove any igor managed profile.

Profiles are created in the default profile 'origin' used by igor (in our case
cobbler is used).
There can also be other origins like e.g. foreman (which is not yet complete
because of a missing power control for real hosts).

Any profile can be used for testin, e.g. with the ``submit`` 

Running a testsuite against a profile and a host
''''''''''''''''''''''''''''''''''''''''''''''''
The testsuites are provided by igor - and described in a different document -
these testsuites can now be run on a host (n our case a libvirt VM) by using
the ``submit`` command.
This command takes a testsuite, profile, and host and optionaly additional
kernel arguments (kargs are inherited from the profile).

Igor will then take then

1. Create a profile (in cobbler)
2. Create a VM (in libvirt)
3. Start and provision the VM via PXE
4. Wait for the testsuite to complete or timeout

All the rest - testing, report pass or failure - is done by the client, part
of the Node/VM/ISO/profile.

Running a testplan against a profile
''''''''''''''''''''''''''''''''''''
A testplan is a list of jobs (testsuite, profile, host, [kargs]) which are run
one after another.
A testplan passes if all jobs in this plan pass. It fails otherwise.
This is mainly to run a et of different testsuites (e.g. one for UI testing,
one for network testing, and another for storage testing) on the same or
different profiles and hosts.

You can run a tesplan by issuing::

    $ $IGOR_BASE/igor/data/igorclient.sh testplan_submit <TESTPLAN>

A testplan wouldn't be to useful if all the entries in the testplan were fixed,
e.g. all hosts and profile need to keep the same name for all time, but this
might not make sense, because e.g. profile names would/should differ for
different e.g. Node releases (2.4.0, 2.5.0, 2.5.0-1).

Therefor tesplans allow variables.
A testplan looks like::

    description:AI and MI with {tbd_profile} on VMs

    # Testsuite             Profile         Host                Optional: kargs

    # A basic manual (TUI) installation
    mi_basic                {tbd_profile}   default-libvirt

    # A basic auto installation without any TUI testing
    ai_basic                {tbd_profile}   default-libvirt     kargs='storage_init BOOTIF=link'

Variables are tokens in curly brackets (in this case ``(tbd_profile}``).
This variables can be replaced when submitting a tesplan by appending a second
parameter::

    $ $IGOR_BASE/igor/data/igorclient.sh \
        testplan_submit <TESTPLAN> \
        "tbd_profile=ovirt-node-2.5.0-1.fc17.iso&another_variable=value"

It is up to the autohr of the testplan what component (host, testsuite,
profile, kargs) is variable. Any token can be replaced by a variable, which is
then passed when submitting the testplan.

**Note**
    Currently the same testplan can only be run once at a time, whereas you can
    submit as many test jobs as you want.

What to do now
--------------
There are different documents for different parts of igor, have a look in the
``$NODE_BASE/igor/tests`` directory for Node specififc documentation and also
in the igor sources for general documentation on e.g. how to write testcases.
