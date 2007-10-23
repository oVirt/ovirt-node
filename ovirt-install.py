#!/usr/bin/python -tt
#
# Script to set up a Xen guest and kick off an install
#
# Copyright 2005-2006  Red Hat, Inc.
# Jeremy Katz <katzj@redhat.com>
# Option handling added by Andrew Puch <apuch@redhat.com>
#
# This software may be freely redistributed under the terms of the GNU
# general public license.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.


import os, sys, string
from optparse import OptionParser, OptionValueError
import subprocess
import logging
import libxml2
import urlgrabber.progress as progress

import libvirt
import virtinst
import virtinst.cli as cli

import gettext
import locale

locale.setlocale(locale.LC_ALL, '')
gettext.bindtextdomain(virtinst.gettext_app, virtinst.gettext_dir)
gettext.install(virtinst.gettext_app, virtinst.gettext_dir)

### General input gathering functions
def get_disk(disk, size, sparse, guest, conn):
    while 1:
        msg = _("What would you like to use as the disk (path)?")
        disk = cli.prompt_for_input(msg, disk)
        # the next few lines are a replacement for:
        # d = virtinst.VirtualDisk(path=disk, type=virtinst.VirtualDisk.TYPE_BLOCK)
        # since the former does stat() checking on the block device (which
        # will be remote in our case
        d = virtinst.VirtualDisk()
        d.type = d._type = virtinst.VirtualDisk.TYPE_BLOCK
        d.path = disk
        guest.disks.append(d)
        break
        
def get_disks(disk, size, sparse, nodisks, guest, conn):
    if nodisks:
        if disk or size:
            raise ValueError, _("Cannot use --file with --nodisks")
        return
    # ensure we have equal length lists 
    if (type(disk) == type(size) == list):
        if len(disk) != len(size):
            print >> sys.stderr, _("Need to pass size for each disk")
            sys.exit(1)
    elif type(disk) == list:
        size = [ None ] * len(disk)
    elif type(size) == list:
        disk = [ None ] * len(size)

    if (type(disk) == list):
        map(lambda d, s: get_disk(d, s, sparse, guest, conn),
            disk, size)
    elif (type(size) == list):
        map(lambda d, s: get_disk(d, s, sparse, guest, conn),
            disk, size)
    else:
        get_disk(disk, size, sparse, guest, conn)

def get_networks(macs, bridges, networks, guest):
    (macs, networks) = cli.digest_networks(macs, bridges, networks)
    map(lambda m, n: cli.get_network(m, n, guest), macs, networks)

### fullvirt input gathering functions
def get_fullvirt_cdrom(cdpath, location, guest):
    # Got a location, then ignore CDROM
    if location is not None:
        guest.location = location
        return

    while 1:
        cdpath = cli.prompt_for_input(_("What is the virtual CD image, CD device or install location?"), cdpath)
        try:
            guest.cdrom = cdpath
            break
        except ValueError, e:
            print _("ERROR: "), e
            cdpath = None

### Option parsing
def check_before_store(option, opt_str, value, parser):
    if len(value) == 0:
        raise OptionValueError, _("%s option requires an argument") %opt_str
    setattr(parser.values, option.dest, value)

def check_before_append(option, opt_str, value, parser):
    if len(value) == 0:
        raise OptionValueError, _("%s option requires an argument") %opt_str
    parser.values.ensure_value(option.dest, []).append(value)

def parse_args():
    parser = OptionParser()
    parser.add_option("-n", "--name", type="string", dest="name",
                      action="callback", callback=cli.check_before_store,
                      help=_("Name of the guest instance"))
    parser.add_option("-r", "--ram", type="int", dest="memory",
                      help=_("Memory to allocate for guest instance in megabytes"))
    parser.add_option("-u", "--uuid", type="string", dest="uuid",
                      action="callback", callback=cli.check_before_store,
                      help=_("UUID for the guest; if none is given a random UUID will be generated. If you specify UUID, you should use a 32-digit hexadecimal number."))
    parser.add_option("", "--vcpus", type="int", dest="vcpus",
                      help=_("Number of vcpus to configure for your guest"))
    parser.add_option("", "--check-cpu", action="store_true", dest="check_cpu",
                      help=_("Check that vcpus do not exceed physical CPUs and warn if they do."))

    # disk options
    parser.add_option("-f", "--file", type="string",
                      dest="diskfile", action="callback", callback=cli.check_before_append,
                      help=_("File to use as the disk image"))
    parser.add_option("-s", "--file-size", type="float",
                      action="append", dest="disksize",
                      help=_("Size of the disk image (if it doesn't exist) in gigabytes"))
    parser.add_option("", "--nonsparse", action="store_false",
                      default=True, dest="sparse",
                      help=_("Don't use sparse files for disks.  Note that this will be significantly slower for guest creation"))
    parser.add_option("", "--nodisks", action="store_true",
                      help=_("Don't set up any disks for the guest."))
    
    # network options
    parser.add_option("-m", "--mac", type="string",
                      dest="mac", action="callback", callback=cli.check_before_append,
                      help=_("Fixed MAC address for the guest; if none or RANDOM is given a random address will be used"))
    parser.add_option("-b", "--bridge", type="string",
                      dest="bridge", action="callback", callback=cli.check_before_append,
                      help=_("Bridge to connect guest NIC to; if none given, will try to determine the default"))
    parser.add_option("-w", "--network", type="string",
                      dest="network", action="callback", callback=cli.check_before_append,
                      help=_("Connect the guest to a virtual network, forwarding to the physical network with NAT"))

    # graphics options
    parser.add_option("", "--vnc", action="store_true", dest="vnc", 
                      help=_("Use VNC for graphics support"))
    parser.add_option("", "--vncport", type="int", dest="vncport",
                      help=_("Port to use for VNC"))
    parser.add_option("", "--sdl", action="store_true", dest="sdl", 
                      help=_("Use SDL for graphics support"))
    parser.add_option("", "--nographics", action="store_true",
                      help=_("Don't set up a graphical console for the guest."))
    parser.add_option("", "--noautoconsole",
                      action="store_false", dest="autoconsole",
                      help=_("Don't automatically try to connect to the guest console"))

    parser.add_option("-k", "--keymap", type="string", dest="keymap",
                      action="callback", callback=cli.check_before_store,
                      help=_("set up keymap for a graphical console"))

    parser.add_option("", "--connect", type="string", dest="connect",
                      action="callback", callback=cli.check_before_store,
                      help=_("Connect to hypervisor with URI"),
                      default=virtinst.util.default_connection())
    parser.add_option("", "--livecd", action="store_true", dest="livecd",
                      help=_("Specify the CDROM media is a LiveCD"))

    # fullvirt options
    parser.add_option("-c", "--cdrom", type="string", dest="cdrom",
                      action="callback", callback=cli.check_before_store,
                      help=_("File to use a virtual CD-ROM device for fully virtualized guests"))
    parser.add_option("", "--pxe", action="store_true", dest="pxe",
                      help=_("Boot an installer from the network using the PXE boot protocol"))
    parser.add_option("", "--os-type", type="string", dest="os_type",
                      action="callback", callback=cli.check_before_store,
                      help=_("The OS type for fully virtualized guests, e.g. 'linux', 'unix', 'windows'"))
    parser.add_option("", "--os-variant", type="string", dest="os_variant",
                      action="callback", callback=cli.check_before_store,
                      help=_("The OS variant for fully virtualized guests, e.g. 'fedora6', 'rhel5', 'solaris10', 'win2k', 'vista'"))
    parser.add_option("", "--noapic", action="store_true", dest="noapic", help=_("Disables APIC for fully virtualized guest (overrides value in os-type/os-variant db)"), default=False)
    parser.add_option("", "--noacpi", action="store_true", dest="noacpi", help=_("Disables ACPI for fully virtualized guest (overrides value in os-type/os-variant db)"), default=False)
    parser.add_option("", "--arch", type="string", dest="arch",
                      default=virtinst.util.get_default_arch(),
                      action="callback", callback=cli.check_before_store,
                      help=_("The CPU architecture to simulate"))
    
    # Misc options
    parser.add_option("-d", "--debug", action="store_true", dest="debug", 
                      help=_("Print debugging information"))


    (options,args) = parser.parse_args()
    return options


### console callback methods
def get_xml_string(dom, path):
    xml = dom.XMLDesc(0)
    try:
        doc = libxml2.parseDoc(xml)
    except:
        return None

    ctx = doc.xpathNewContext()
    try:
        ret = ctx.xpathEval(path)
        tty = None
        if len(ret) == 1:
            tty = ret[0].content
        ctx.xpathFreeContext()
        doc.freeDoc()
        return tty
    except Exception, e:
        ctx.xpathFreeContext()
        doc.freeDoc()
        return None

def vnc_console(dom, uri):
    args = ["/usr/bin/virt-viewer"]
    if uri is not None and uri != "":
        args = args + [ "--connect", uri]
    args = args + [ "--wait", "%s" % dom.ID()]
    child = os.fork()
    if not child:
        os.execvp(args[0], args)
        os._exit(1)

    return child

def txt_console(dom, uri):
    args = ["/usr/bin/virsh"]
    if uri is not None and uri != "":
        args = args + [ "--connect", uri]
    args = args + [ "console", "%s" % dom.ID()]
    child = os.fork()
    if not child:
        os.execvp(args[0], args)
        os._exit(1)

    return child

### Let's do it!
def main():
    options = parse_args()

    cli.setupLogging("ovirt-install", options.debug)
    conn = cli.getConnection(options.connect)
    type = None

    options.location = None

    type = "qemu"
    if virtinst.util.is_kvm_capable():
        type = "kvm"
    elif virtinst.util.is_kqemu_capable():
        type = "kqemu"

    if options.livecd:
        installer = virtinst.LiveCDInstaller(type = type)
    elif options.pxe:
        installer = virtinst.PXEInstaller(type = type)
    else:
        installer = virtinst.DistroInstaller(type = type)

    if (options.pxe and options.location) or (options.location and options.cdrom) or (options.cdrom and options.pxe):
        print >> sys.stderr, _("Only one of --pxe, --location and --cdrom can be used")
        sys.exit(1)

    guest = virtinst.FullVirtGuest(connection=conn, installer=installer, arch=options.arch)

    # now let's get some of the common questions out of the way
    cli.get_name(options.name, guest)
    cli.get_memory(options.memory, guest)
    cli.get_uuid(options.uuid, guest)
    cli.get_vcpus(options.vcpus, options.check_cpu, guest, conn)

    # OVIRT: FIXME: this is where we need to do remote stuff for disks
    # set up disks
    get_disks(options.diskfile, options.disksize, options.sparse,
              options.nodisks, guest, conn)

    # set up network information
    get_networks(options.mac, options.bridge, options.network, guest)

    # set up graphics information
    cli.get_graphics(options.vnc, options.vncport, options.nographics, options.sdl, options.keymap, guest)

    if not options.pxe:
        get_fullvirt_cdrom(options.cdrom, options.location, guest)
    if options.noacpi:
        guest.features["acpi"] = False
    if options.noapic:
        guest.features["apic"] = False
    if options.os_type is not None:
        guest.set_os_type(options.os_type)
        if options.os_variant is not None:
            guest.set_os_variant(options.os_variant)
    continue_inst = guest.get_continue_inst()

    def show_console(dom):
        if guest.graphics["enabled"]:
            if guest.graphics["type"].name == "vnc":
                return vnc_console(dom, options.connect)
            else:
                return None # SDL needs no viewer app
        else:
            return txt_console(dom, options.connect)

    if options.autoconsole is False:
        conscb = None
    else:
        conscb = show_console

    progresscb = progress.TextMeter()

    #guest._prepare_install(progresscb)
    #print guest.get_config_xml()
    #sys.exit(100)

    # we've got everything -- try to start the install
    try:
        print _("\n\nStarting install...")

        started = False
        while True:
            if not started:
                dom = guest.start_install(conscb,progresscb)
            elif continue_inst:
                dom = guest.continue_install(conscb,progresscb)
                continue_inst = False
            else:
                break

            if dom is None:
                print _("Guest installation failed")
                sys.exit(0)
            elif dom.info()[0] != libvirt.VIR_DOMAIN_SHUTOFF:
                # domain seems to be running
                print _("Domain installation still in progress.  You can reconnect to \nthe console to complete the installation process.")
                sys.exit(0)

            if not started:
                started = True
                if not guest.post_install_check():
                    print _("Domain installation does not appear to have been\n successful.  If it was, you can restart your domain\n by running 'virsh start %s'; otherwise, please\n restart your installation.") %(guest.name,)
                    sys.exit(0)

        print _("Guest installation complete... restarting guest.")
        dom.create()
        guest.connect_console(conscb)
    except RuntimeError, e:
        print >> sys.stderr, _("ERROR: "), e
        sys.exit(1)
    except SystemExit, e:
        sys.exit(e.code)
    except Exception, e:
        print str(e)
        print _("Domain installation may not have been\n successful.  If it was, you can restart your domain\n by running 'virsh start %s'; otherwise, please\n restart your installation.") %(guest.name,)
        raise

if __name__ == "__main__":
    try:
        main()
    except SystemExit, e:
        sys.exit(e.code)
    except Exception, e:
        logging.exception(e)
