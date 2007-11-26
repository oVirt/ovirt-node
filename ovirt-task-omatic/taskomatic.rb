#!/usr/bin/ruby

require 'active_record'
require 'erb'
require 'libvirt'
require 'rexml/document'
include REXML

require '../wui/src/app/models/task.rb'
require '../wui/src/app/models/host.rb'
require '../wui/src/app/models/vm.rb'

def database_configuration
  YAML::load(ERB.new(IO.read('../wui/src/config/database.yml')).result)
end

def create_vm_xml(name, uuid, memAllocated, memUsed, vcpus, macAddr, bridge,
                  disk_device)
  doc = Document.new

  doc.add_element("domain", {"type" => "kvm"})
  
  doc.root.add_element("name")
  doc.root.elements["name"].text = name
  
  doc.root.add_element("uuid")
  doc.root.elements["uuid"].text = uuid
  
  doc.root.add_element("memory")
  doc.root.elements["memory"].text = memAllocated
  
  doc.root.add_element("currentMemory")
  doc.root.elements["currentMemory"].text = memUsed
  
  doc.root.add_element("vcpu")
  doc.root.elements["vcpu"].text = vcpus
  
  doc.root.add_element("os")
  doc.root.elements["os"].add_element("type")
  doc.root.elements["os"].elements["type"].text = "hvm"
  doc.root.elements["os"].add_element("boot", {"dev" => "network"})
  
  doc.root.add_element("clock", {"offset" => "utc"})
  
  doc.root.add_element("on_poweroff")
  doc.root.elements["on_poweroff"].text = "destroy"
  
  doc.root.add_element("on_reboot")
  doc.root.elements["on_reboot"].text = "restart"
  
  doc.root.add_element("on_crash")
  doc.root.elements["on_crash"].text = "destroy"
  
  doc.root.add_element("devices")
  doc.root.elements["devices"].add_element("emulator")
  doc.root.elements["devices"].elements["emulator"].text = "/usr/bin/qemu-kvm"
  doc.root.elements["devices"].add_element("disk", {"type" => "block", "device" => "disk"})
  doc.root.elements["devices"].elements["disk"].add_element("source", {"dev" => disk_device})
  doc.root.elements["devices"].elements["disk"].add_element("target", {"dev" => "hda"})
  doc.root.elements["devices"].add_element("interface", {"type" => "bridge"})
  doc.root.elements["devices"].elements["interface"].add_element("mac", {"address" => macAddr})
  doc.root.elements["devices"].elements["interface"].add_element("source", {"bridge" => bridge})
  doc.root.elements["devices"].elements["interface"].add_element("target", {"dev" => "vnet0"})
  doc.root.elements["devices"].add_element("input", {"type" => "mouse", "bus" => "ps2"})
  doc.root.elements["devices"].add_element("graphics", {"type" => "vnc", "port" => "-1", "listen" => "0.0.0.0"})

  return doc
end

def setTaskState(task, state, msg => nil)
  task.state = state
  task.msg = msg
  task.save
end

def findVM(task, fail_on_nil_host_id => true)
  # first, find the matching VM in the vms table
  vm = Vm.find(:first, :conditions => [ "id = ?", task.vm_id ])
  
  if vm == nil
    puts "No VM found"
    setTaskState(task, Task.STATE_FAILED, "VM id " + task.vm_id + "not found")
    raise
  end

  if vm.host_id == nil && fail_on_nil_host_id
    # in this case, we have no idea where the VM is.  How can we handle this
    # gracefully?  We don't necessarily want to just set the VM state to off;
    # if the machine does happen to be running somewhere and we set it to
    # disabled here, and then start it again, we could corrupt the disk

    # FIXME: the right thing to do here is probably to contact all of the
    # hosts we know about and ensure that the domain isn't running; then we
    # can mark it either as off (if we didn't find it), or mark the correct
    # vm.host_id if we did.  However, if you have a large number of hosts
    # out there, this could take a while.
    setTaskState(task, Task.STATE_FAILED, "No host_id for VM" + task.vm_id)
    raise
  end

  return vm
end

def findHost(task, vm)
  host = Host.find(:first, :conditions => [ "id = ?", vm.host_id])
  puts host

  if host == nil
    # Hm, we didn't find the host_id.  Seems odd.  Return a failure

    # FIXME: we should probably contact the hosts we know about and check to
    # see if this VM is running
    setTaskState(task, Task.STATE_FAILED, "Could not find the host that VM is running on")
    raise
  end

  return host
end

=begin
def checkVMState(current, op)
  case op
  when Task.ACTION_INSTALL_VIRT then
  when Task.ACTION_SHUTDOWN_VIRT then
    if current == Vm.STATE_STOPPED
      raise "already shutdown"
    elsif current == Vm.STATE_PAUSED || current == Vm.STATE_SAVED
      raise "cannot shutdown paused or saved VM"
    end
  when Task.ACTION_START_VIRT then start_vm(task)
  when Task.ACTION_PAUSE_VIRT then suspend_vm(task)
  when Task.ACTION_UNPAUSE_VIRT then resume_vm(task)
  when Task.ACTION_SAVE_VIRT then save_vm(task)
  when Task.ACTION_RESTORE_VIRT then restore_vm(task)
  else raise
  end
end
=end

$dbconfig = database_configuration
$develdb = $dbconfig['development']
ActiveRecord::Base.establish_connection(
                                        :adapter  => $develdb['adapter'],
                                        :host     => $develdb['host'],
                                        :username => $develdb['username'],
                                        :password => $develdb['password'],
                                        :database => $develdb['database']
                                        )

def create_vm(task)
  puts "create_vm"

  # since we are actually generating XML on the fly in the "start_vm" method,
  # we don't actually need to do much here.  We might need to allocate disk
  # space, etc, but we can skip that for now

  # FIXME: what do we do about attaching a CDROM for first install?

  setTaskState(task, Task.STATE_FINISHED)
end

def shutdown_vm(task)
  puts "shutdown_vm"

  # here, we are given an id for a VM to shutdown; we have to lookup which
  # physical host it is running on

  begin
    vm = findVM(task)
  rescue
    return
  end

  if vm.state == Vm.STATE_STOPPED
    # the VM is already shutdown; just return success
    setTaskState(task, Task.STATE_FINISHED)
    vm.host_id = nil
    vm.save
    return
  elsif vm.state == Vm.STATE_PAUSED || vm.state == Vm.STATE_SAVED
    # FIXME: hm, we have two options here: either resume the VM and then
    # shut it down below, or fail.  I'm leaning towards fail
    setTaskState(task, Task.STATE_FAILED, "Cannot shutdown paused domain")
    return
  end

  # OK, now that we found the VM, go looking in the hosts table
  begin
    host = findHost(task, vm)
  rescue
    return
  end

  begin
    conn = Libvirt::open("qemu+tls://" + host.hostname + "/system")
    dom = conn.lookupDomainByUUID(vm.uuid)
    dom.shutdown
    dom.undefine
  rescue
    setTaskState(task, Task.STATE_FAILED, "Error looking up domain " + vm.uuid)
    return
  end

  conn.close

  setTaskState(task, Task.STATE_FINISHED)

  vm.host_id = nil
  vm.state = Vm.STATE_STOPPED
  vm.save
end

def start_vm(task)
  puts "start_vm"

  # here, we are given an id for a VM to start

  begin
    vm = findVM(task, false)
  rescue
    return
  end

  # the VM might be in an inconsistent state in the database; however, we
  # should check it out on the remote host, and update the database as
  # appropriate

  if vm.host_id != nil
    # OK, marked in the database as already running on a host; let's check it

    host = Host.find(:first, :conditions => [ "id = ?", vm.host_id ])
    if host != nil
      # we found the host it is running on; let's check to see if libvirt
      # thinks that VM is running

      conn = Libvirt::open("qemu+tls://" + host.hostname + "/system")
      begin
        dom = conn.lookupDomainByUUID(vm.uuid)
      rescue
        # if we failed here, we couldn't find that UUID on the host.  Let's
        # update the DB here
        # FIXME: there are other reasons that this can fail, but the error
        # reporting the ruby bindings don't seem very good right now
        dom = nil
      end

      if dom != nil
        # OK, this VM is defined on this host; let's look at the state

        info = dom.info
        if info.state == dom.RUNNING || info.state == dom.BLOCKED
          # we found it on the remote host, and it was already running
          setTaskState(task, Task.STATE_FINISHED)
          vm.state = Vm.STATE_RUNNING
          vm.save
          return
        elsif info.state == dom.SHUTDOWN || info.state == dom.SHUTOFF || info.state == dom.CRASHED || info.state == dom.NOSTATE
          # in these states, we want to undefine it so we can start it down
          # below
          # FIXME: especially in the "CRASHED" case, we probably want to record
          # what happened somewhere
          dom.undefine
        elsif info.state == dom.PAUSED
          # the domain is defined, but paused.  We can't start it again
          setTaskState(task, Task.STATE_FAILED, "Domain paused")
          return
        end
      else
        # we couldn't find the domain running on that host; update the database
        vm.host_id = nil
        vm.save
      end
    else
      # hm, the VM was marked as running on a host, but we couldn't find that
      # host in the database; return an error

      setTaskState(task, Task.STATE_FAILED, "Could not find host in the database")
      return
    end
  end

  # OK, now that we found the VM, go looking in the hosts table to see if there
  # is a host that will fit these constraints
  host = Host.find(:first, :conditions => [ "num_cpus >= ? AND memory >= ?",
                                            vm.num_vcpus_allocated,
                                            vm.memory_allocated])

  if host == nil
    # we couldn't find a host that matches this description; report ERROR
    setTaskState(task, Task.STATE_FAILED, "No host matching VM parameters could be found")
    return
  end

  # OK, we found a host that will work; now let's build up the XML

  # FIXME: get rid of the hardcoded bridge and disk here
  xml = create_vm_xml(vm.description, vm.uuid, vm.memory_allocated,
                      vm.memory_used, vm.num_vcpus_used, vm.vnic_mac_addr,
                      "ovirtbr0",
                      "/dev/disk/by-id/scsi-16465616462656166313a3300000000000000000000000000")

  begin
    conn = Libvirt::open("qemu+tls://" + host.hostname + "/system")
    dom = conn.defineDomainXML(xml.to_s)
    dom.create
  rescue
    # FIXME: these may fail for various reasons:
    # 1.  The domain is already defined and/or started - update the DB
    # 2.  We couldn't define the domain for some reason
    setTaskState(task, Task.STATE_FAILED, "Libvirt error")
    return
  end

  conn.close

  vm.host_id = host.id
  vm.state = Vm.STATE_RUNNING
  setTaskState(task, Task.STATE_FINISHED)

  vm.save
end

def save_vm(task)
  puts "save_vm"

  # here, we are given an id for a VM to suspend

  begin
    vm = findVM(task)
  rescue
    return
  end

  if vm.state == Vm.STATE_SAVED
    # the VM is already saved; just return success
    setTaskState(task, Task.STATE_FINISHED)
    return
  elsif vm.state == Vm.STATE_PAUSED
    # FIXME: hm, we have two options here: either resume the VM and then
    # save it down below, or fail.  I'm leaning towards fail
    setTaskState(task, Task.STATE_FAILED, "Cannot save paused domain")
    return    
  elsif vm.state == Vm.STATE_STOPPED
    setTaskState(task, Task.STATE_FAILED, "Cannot save shutdown domain")
    return
  end

  # OK, now that we found the VM, go looking in the hosts table
  begin
    host = findHost(task, vm)
  rescue
    return
  end

  begin
    conn = Libvirt::open("qemu+tls://" + host.hostname + "/system")
    dom = conn.lookupDomainByUUID(vm.uuid)
    dom.save("/tmp/" + vm.uuid + ".save")
  rescue
    setTaskState(task, Task.STATE_FAILED, "Save failed")
    return
  end

  conn.close

  # note that we do *not* reset the host_id here, since we stored the saved
  # vm state information locally.  restore_vm will pick it up from here

  # FIXME: it would be much nicer to be able to save the VM and remove the
  # the host_id and undefine the XML; that way we could resume it on another
  # host later.  This needs more thought

  vm.state = Vm.STATE_SAVED
  setTaskState(task, Task.STATE_FINISHED)

  vm.save
end

def restore_vm(task)
  puts "restore_vm"

  # here, we are given an id for a VM to start

  begin
    vm = findVM(task)
  rescue
    return
  end

  # OK, marked in the database as already running on a host; let's check it

  host = Host.find(:first, :conditions => [ "id = ?", vm.host_id ])
  if host == nil
    # hm, the VM was marked as running on a host, but we couldn't find that
    # host in the database; return an error

    setTaskState(task, Task.STATE_FAILED, "Could not find host in the database")
    return
  end

  # we found the host it is running on; let's check to see if libvirt
  # thinks that VM is running
  
  begin
    conn = Libvirt::open("qemu+tls://" + host.hostname + "/system")
    dom = conn.lookupDomainByUUID(vm.uuid)
  rescue
    # if we failed here, we couldn't find that UUID on the host.  We have to
    # fail
    setTaskState(task, Task.STATE_FAILED, "Could not find paused VM " + vm.uuid)
    return
  end
  
  if dom == nil
    # we couldn't find a host that matches this description; report ERROR
    setTaskState(task, Task.STATE_FAILED, "Could not find paused VM " + vm.uuid)
    return
  end

  # OK, this VM is defined on this host; let's look at the state
    
  info = dom.info
  if info.state == dom.RUNNING || info.state == dom.BLOCKED
    # we found it on the remote host, and it was already running
    setTaskState(task, Task.STATE_FAILED, "Error: domain already running")
    vm.state = Vm.STATE_RUNNING
    vm.save
    return
  elsif info.state == dom.PAUSED
    # the domain is defined, but paused.  We can't start it again
    setTaskState(task, Task.STATE_FAILED, "Domain paused")
    return
  end
  
  begin
    conn = Libvirt::open("qemu+tls://" + host.hostname + "/system")
    dom = conn.lookupDomainByUUID(vm.uuid)
    dom.restore
  rescue
    # FIXME: these may fail for various reasons:
    # 1.  The domain is already defined and/or started - update the DB
    # 2.  We couldn't define the domain for some reason
    setTaskState(task, Task.STATE_FAILED, "Libvirt error")
    return
  end

  conn.close

  vm.state = Vm.STATE_RUNNING
  setTaskState(task, Task.STATE_FINISHED)

  vm.save
end

def suspend_vm(task)
  puts "suspend_vm"

  # here, we are given an id for a VM to suspend; we have to lookup which
  # physical host it is running on

  begin
    vm = findVM(task)
  rescue
    return
  end

  if vm.state == Vm.STATE_PAUSED
    # the VM is already paused; just return success
    setTaskState(task, Task.STATE_FINISHED)
    return
  elsif vm.state == Vm.STATE_STOPPED || vm.state == Vm.STATE_SAVED
    # FIXME: hm, we have two options here: either resume the VM and then
    # pause it down below, or fail.  I'm leaning towards fail
    setTaskState(task, Task.STATE_FAILED, "Cannot shutdown paused domain")
    return
  end

  # OK, now that we found the VM, go looking in the hosts table
  begin
    host = findHost(task, vm)
  rescue
    return
  end

  begin
    conn = Libvirt::open("qemu+tls://" + host.hostname + "/system")
    dom = conn.lookupDomainByUUID(vm.uuid)
    dom.suspend
  rescue
    setTaskState(task, Task.STATE_FAILED, "Error looking up domain " + vm.uuid)
    return
  end

  conn.close

  # note that we do *not* reset the host_id here, since we just paused the VM
  # resume_vm will pick it up from here

  vm.state = Vm.STATE_PAUSED
  setTaskState(task, Task.STATE_FINISHED)

  vm.save
end

def resume_vm(task)
  puts "resume_vm"

  # here, we are given an id for a VM to start

  begin
    vm = findVM(task)
  rescue
    return
  end

  # OK, marked in the database as already running on a host; let's check it

  host = Host.find(:first, :conditions => [ "id = ?", vm.host_id ])

  if host == nil
    setTaskState(task, Task.STATE_FAILED, "No host matching VM parameters could be found")
    return
  end

  # we found the host it is running on; let's check to see if libvirt
  # thinks that VM is running

  begin
    conn = Libvirt::open("qemu+tls://" + host.hostname + "/system")
    dom = conn.lookupDomainByUUID(vm.uuid)
  rescue
    # if we failed here, we couldn't find that UUID on the host.  We have to
    # fail
    setTaskState(task, Task.STATE_FAILED, "Could not find paused VM " + vm.uuid)
    return
  end

  if dom == nil
    # we couldn't find a host that matches this description; report ERROR
    setTaskState(task, Task.STATE_FAILED, "Could not find paused VM " + vm.uuid)
    return
  end

  # OK, this VM is defined on this host; let's look at the state
  
  info = dom.info
  if info.state != dom.PAUSED
    setTaskState(task, Task.STATE_FAILED, "VM " + vm.uuid + "is not paused")
    return
  end
  
  # OK, we found a host that will work; now let's build up the XML

  begin
    conn = Libvirt::open("qemu+tls://" + host.hostname + "/system")
    dom = conn.lookupDomainByUUID(vm.uuid)
    dom.resume
  rescue
    setTaskState(task, Task.STATE_FAILED, "Error looking up domain " + vm.uuid)
    return
  end

  conn.close
  
  vm.state = Vm.STATE_RUNNING
  setTaskState(task, Task.STATE_FINISHED)
  
  vm.save
end

while(true)
  puts 'Checking for tasks...'
  
  Task.find(:all, :conditions => [ "state = ?", Task.STATE_QUEUED ]).each do |task|
    case task.action
    when Task.ACTION_INSTALL_VIRT then create_vm(task)
    when Task.ACTION_SHUTDOWN_VIRT then shutdown_vm(task)
    when Task.ACTION_START_VIRT then start_vm(task)
    when Task.ACTION_PAUSE_VIRT then suspend_vm(task)
    when Task.ACTION_UNPAUSE_VIRT then resume_vm(task)
    when Task.ACTION_SAVE_VIRT then save_vm(task)
    when Task.ACTION_RESTORE_VIRT then restore_vm(task)
    else puts "unknown task" + task.action
    end
  end
  
  sleep 5
end
