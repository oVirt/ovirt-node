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
  puts task
  puts task.vm_id

  # since we are actually generating XML on the fly in the "start_vm" method,
  # we don't actually need to do much here.  We might need to allocate disk
  # space, etc, but we can skip that for now

  task.state = "SUCCESS"
end

def shutdown_vm(task)
  puts "shutdown_vm"

  # here, we are given a UUID for a VM to shutdown; we have to lookup which
  # physical host it is running on

  # first, find the matching VM in the vms table
  vm = Vm.find(:first, :conditions => [ "id = ?", task.vm_id ])
  
  if vm == nil
    puts "No VM found"
    task.state = "ERROR: VM id " + task.vm_id + "not found"
    return    
  end

  if vm.state == "SHUTDOWN"
    # the VM is already shutdown; just return success
    task.state = "SUCCESS"
    vm.host_id = nil
    return
  end

  if vm.host_id == nil
    # in this case, we have no idea where the VM is.  How can we handle this
    # gracefully?  We don't necessarily want to just set the VM state to off;
    # if the machine does happen to be running somewhere, bye-bye disk.

    # FIXME: the right thing to do here is probably to contact all of the
    # hosts we know about and ensure that the domain isn't running; then we
    # can mark it either as off (if we didn't find it), or mark the correct
    # vm.host_id if we did.  However, if you have a large number of hosts
    # out there, this could take a while.
    task.state = "ERROR: No host_id for VM" + task.vm_id
    return
  end

  # OK, now that we found the VM, go looking in the hosts table to see if there
  # is a host that will fit these constraints
  host = Host.find(:first, :conditions => [ "id = ?", vm.host_id])
  puts host

  if host == nil
    # Hm, we didn't find the host_id.  Seems odd.  Return a failure

    # FIXME: we should probably contact the hosts we know about and check to
    # see if this VM is running
    task.state = "ERROR: Could not find the host that VM is running on"
    return
  end

  # FIXME: handle libvirt exceptions

  conn = Libvirt::open("qemu+tls://" + host.hostname + "/system")

  dom = conn.lookupDomainByUUID(vm.uuid)
  dom.shutdown
  dom.undefine

  conn.close
end

def start_vm(task)
  puts "start_vm"

  # here, we are given an id for a VM to start

  # first, find the matching VM in the vms table
  vm = Vm.find(:first, :conditions => [ "id = ?", task.vm_id ])
  
  if vm == nil
    puts "No VM found"
    task.state = "ERROR: VM id " + task.vm_id + "not found"
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
      dom = conn.lookupDomainByUUID(vm.uuid)
      if dom != nil
        # OK, this VM is defined on this host; let's look at the state

        info = dom.info
        if info.state == dom.RUNNING || info.state == dom.BLOCKED
          # we found it on the remote host, and it was already running
          vm.state = "RUNNING"
          task.state = "SUCCESS"
          return
        elsif info.state == dom.SHUTDOWN || info.state == dom.SHUTOFF
          || info.state == dom.CRASHED || info.state == dom.NOSTATE
          # in these states, we want to undefine it so we can start it down
          # below
          # FIXME: especially in the "CRASHED" case, we probably want to record
          # what happened somewhere
          dom.undefine
        elsif info.state == dom.PAUSED
          # the domain is defined, but paused.  We can't start it again
          task.state = "ERROR: Domain paused"
          return
        end
      end
    end
  end

  # OK, now that we found the VM, go looking in the hosts table to see if there
  # is a host that will fit these constraints
  host = Host.find(:first, :conditions => [ "num_cpus >= ? AND memory >= ?",
                                            vm.num_vcpus_allocated,
                                            vm.memory_allocated])
  puts host

  if host == nil
    # we couldn't find a host that matches this description; report ERROR
    task.state = "ERROR: No host matching VM parameters could be found"
    return
  end

  # OK, we found a host that will work; now let's build up the XML

  xml = create_vm_xml(vm.description, vm.uuid, vm.memory_allocated,
                      vm.memory_used, vm.num_vcpus_used, vm.vnic_mac_addr,
                      "ovirtbr0",
                      "/dev/disk/by-id/scsi-16465616462656166313a3300000000000000000000000000")

  # FIXME: handle exceptions

  conn = Libvirt::open("qemu+tls://" + host.hostname + "/system")
  dom = conn.defineDomainXML(xml)
  dom.create
  conn.close

  vm.host_id = host.id
  vm.state = "RUNNING"
  task.state = "SUCCESS"
end

def suspend_vm(task)
end

def resume_vm(task)
end

while(true)
  puts 'Checking for tasks...'

  Task.find(:all, :conditions => [ "state IS NULL" ]).each do |task|
    case task.action
      when "create_vm" then create_vm(task)
      when "shutdown_vm" then shutdown_vm(task)
      when "start_vm" then start_vm(task)
      when "suspend_vm" then suspend_vm(task)
      when "resume_vm" then resume_vm(task)
      else puts "unknown"
    end
  end

  sleep 5
end
