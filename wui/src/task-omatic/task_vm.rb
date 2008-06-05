# Copyright (C) 2008 Red Hat, Inc.
# Written by Chris Lalancette <clalance@redhat.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.  A copy of the GNU General Public License is
# also available at http://www.gnu.org/copyleft/gpl.html.

require 'rexml/document'
include REXML

require 'utils'

def create_vm_xml(name, uuid, memAllocated, memUsed, vcpus, bootDevice,
                  macAddr, bridge, diskDevices)
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
  doc.root.elements["os"].add_element("boot", {"dev" => bootDevice})
  
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

  devs = [ 'hda', 'hdb', 'hdc', 'hdd' ]
  i = 0
  diskDevices.each do |disk|
    diskdev = Element.new("disk")
    diskdev.add_attribute("type", "block")
    diskdev.add_attribute("device", "disk")
    diskdev.add_element("source", {"dev" => disk})
    diskdev.add_element("target", {"dev" => devs[i]})
    doc.root.elements["devices"] << diskdev
    i += 1
  end

  doc.root.elements["devices"].add_element("interface", {"type" => "bridge"})
  doc.root.elements["devices"].elements["interface"].add_element("mac", {"address" => macAddr})
  doc.root.elements["devices"].elements["interface"].add_element("source", {"bridge" => bridge})
  doc.root.elements["devices"].add_element("input", {"type" => "mouse", "bus" => "ps2"})
  doc.root.elements["devices"].add_element("graphics", {"type" => "vnc", "port" => "-1", "listen" => "0.0.0.0"})

  return doc
end

def setVmState(vm, state)
  vm.state = state
  vm.save
end

def findVM(task, fail_on_nil_host_id = true)
  # find the matching VM in the vms table
  vm = Vm.find(:first, :conditions => [ "id = ?", task.vm_id ])
  
  if vm == nil
    puts "No VM found"
    setTaskState(task, Task::STATE_FAILED, "VM id " + task.vm_id + "not found")
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
    setTaskState(task, Task::STATE_FAILED, "No host_id for VM " + task.vm_id.to_s)
    raise
  end

  return vm
end

def findHost(task, host_id)
  host = Host.find(:first, :conditions => [ "id = ?", host_id])

  if host == nil
    # Hm, we didn't find the host_id.  Seems odd.  Return a failure
    raise
  end

  return host
end

def setVmShutdown(vm)
  vm.host_id = nil
  vm.memory_used = nil
  vm.num_vcpus_used = nil
  vm.state = Vm::STATE_STOPPED
  vm.needs_restart = nil
  vm.save
end

def create_vm(task)
  puts "create_vm"

  begin
    vm = findVM(task, false)
  rescue
    return
  end

  if vm.state != Vm::STATE_PENDING
    setTaskState(task, Task::STATE_FAILED, "VM not pending")
    return
  end

  setVmState(vm, Vm::STATE_CREATING)
  setTaskState(task, Task::STATE_RUNNING)

  # FIXME: in here, we would do any long running creating tasks (allocating
  # disk, etc.)

  setVmState(vm, Vm::STATE_STOPPED)
  setTaskState(task, Task::STATE_FINISHED)  
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

  if vm.state == Vm::STATE_STOPPED
    # the VM is already shutdown; just return success
    setTaskState(task, Task::STATE_FINISHED)
    setVmShutdown(vm)
    return
  elsif vm.state == Vm::STATE_SUSPENDED
    setTaskState(task, Task::STATE_FAILED, "Cannot shutdown suspended domain")
    return
  elsif vm.state == Vm::STATE_SAVED
    setTaskState(task, Task::STATE_FAILED, "Cannot shutdown saved domain")
    return    
  end

  vm_orig_state = vm.state
  setVmState(vm, Vm::STATE_STOPPING)

  begin
    # OK, now that we found the VM, go looking in the hosts table
    begin
      host = findHost(task, vm.host_id)
    rescue
      setTaskState(task, Task::STATE_FAILED, "Could not find the host that VM is running on")
      raise
    end
    
    begin
      conn = Libvirt::open("qemu+tcp://" + host.hostname + "/system")
      dom = conn.lookup_domain_by_uuid(vm.uuid)
      # FIXME: crappy.  Right now we destroy the domain to make sure it
      # really went away.  We really want to shutdown the domain to make
      # sure it gets a chance to cleanly go down, but how can we tell when
      # it is truly shut off?  And then we probably need a timeout in case
      # of problems.  Needs more thought
      #dom.shutdown
      dom.destroy
      dom.undefine
      conn.close
      # FIXME: hm.  We probably want to undefine the storage pool that this host
      # was using if and only if it's not in use by another VM.
    rescue
      # FIXME: we could get out of sync with the host here, for instance, by the
      # user typing "shutdown" inside the guest.  That would actually shutdown
      # the guest, and the host would know about it, but we would not.  The
      # solution here is to be more selective in which exceptions we handle; a
      # connection exception we just want to fail, but if we fail to find the
      # ID on the host, we should probably still mark it shut off to regain
      # consistency
      setTaskState(task, Task::STATE_FAILED, "Error looking up domain " + vm.uuid)
      raise
    end
  rescue
    setVmState(vm, vm_orig_state)
  end

  setTaskState(task, Task::STATE_FINISHED)

  setVmShutdown(vm)
end

def start_vm(task)
  puts "start_vm"

  # here, we are given an id for a VM to start

  begin
    vm = findVM(task, false)
  rescue
    return
  end

  if vm.state == Vm::STATE_RUNNING
    # the VM is already running; just return success
    setTaskState(task, Task::STATE_FINISHED)
    return
  elsif vm.state == Vm::STATE_SUSPENDED
    setTaskState(task, Task::STATE_FAILED, "Cannot start suspended domain")
    return
  elsif vm.state == Vm::STATE_SAVED
    setTaskState(task, Task::STATE_FAILED, "Cannot start saved domain")
    return
  end

  # FIXME: Validate that the VM is still within quota
  #vm.validate

  vm_orig_state = vm.state
  setVmState(vm, Vm::STATE_STARTING)

  errmsg = "Unknown error"
  begin
    if vm.host_id != nil
      # OK, marked in the database as already running on a host; for now, we
      # will just fail the operation
      
      # FIXME: we probably want to go out to the host it is marked on and check
      # things out, just to make sure things are consistent
      errmsg = "VM already running"      
      raise
    end
    
    # OK, now that we found the VM, go looking in the hardware_pool
    # hosts to see if there is a host that will fit these constraints
    host = nil

    vm.vm_resource_pool.get_hardware_pool.hosts.each do |host|
      if host.num_cpus >= vm.num_vcpus_allocated \
        and host.memory >= vm.memory_allocated \
        and not host.is_disabled
        host = curr
        break
      end
    end

    if host == nil
      # we couldn't find a host that matches this description; report ERROR
      errmsg = "No host matching VM parameters could be found"
      raise
    end

    conn = Libvirt::open("qemu+tcp://" + host.hostname + "/system")

    # here, build up a list of already defined pools.  We'll use it
    # later to see if we need to define new pools for the storage or just
    # keep using existing ones

    defined_pools = []
    all_storage_pools(conn).each do |remote_pool_name|
      tmppool = conn.lookup_storage_pool_by_name(remote_pool_name)
      defined_pools << tmppool
    end

    storagedevs = []
    vm.storage_volumes.each do |volume|
      # here, we need to iterate through each volume and possibly attach it
      # to the host we are going to be using
      storage_pool = volume.storage_pool

      if storage_pool == nil
        # Hum.  Specified by the VM description, but not in the storage pool?
        # continue on and hope for the best
        next
      end

      if storage_pool[:type] == "IscsiStoragePool"
        thisstorage = Iscsi.new(storage_pool.ip_addr, storage_pool[:target])
      elsif storage_pool[:type] == "NfsStoragePool"
        thisstorage = NFS.new(storage_pool.ip_addr, storage_pool.export_path)
      else
        # Hm, a storage type we don't understand; skip it
        next
      end

      thepool = nil
      defined_pools.each do |pool|
         doc = Document.new(pool.xml_desc(0))
         root = doc.root

         if thisstorage.xmlequal?(doc.root)
           thepool = pool
           break
         end
      end

      if thepool == nil
        thepool = conn.define_storage_pool_xml(thisstorage.getxml, 0)
        thepool.build(0)
        thepool.create(0)
      elsif thepool.info.state == Libvirt::StoragePool::INACTIVE
        # only try to start the pool if it is currently inactive; in all other
        # states, assume it is already running
        begin
          thepool.create(0)
        rescue
          # this can fail, for instance, if the remote storage that the user
          # put in is not actually available.  We just return here with a failure;
          # there's not a lot more we can do
          setTaskState(task, Task::STATE_FAILED,"Could not create storage volume")
          conn.close
          errmsg = "Unable to activate storage volume"
          raise
        end
      end

      storagedevs << thepool.lookup_volume_by_name(volume.read_attribute(thisstorage.db_column)).path
    end

    conn.close

    if storagedevs.length > 4
      errmsg = "Too many storage volumes; maximum is 4"
      raise
    end

    # OK, we found a host that will work; now let's build up the XML

    # FIXME: get rid of the hardcoded bridge
    xml = create_vm_xml(vm.description, vm.uuid, vm.memory_allocated,
                        vm.memory_used, vm.num_vcpus_allocated, vm.boot_device,
                        vm.vnic_mac_addr, "ovirtbr0", storagedevs)

    begin
      conn = Libvirt::open("qemu+tcp://" + host.hostname + "/system")
      dom = conn.define_domain_xml(xml.to_s)
      dom.create
      conn.close
    rescue
      # FIXME: these may fail for various reasons:
      # 1.  The domain is already defined and/or started - update the DB
      # 2.  We couldn't define the domain for some reason
      errmsg = "Libvirt error"
      raise
    end
  rescue
    setTaskState(task, Task::STATE_FAILED, errmsg)
    setVmState(vm, vm_orig_state)
    return
  end

  setTaskState(task, Task::STATE_FINISHED)

  vm.host_id = host.id
  vm.state = Vm::STATE_RUNNING
  vm.memory_used = vm.memory_allocated
  vm.num_vcpus_used = vm.num_vcpus_allocated
  vm.boot_device = Vm::BOOT_DEV_HD
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

  if vm.state == Vm::STATE_SAVED
    # the VM is already saved; just return success
    setTaskState(task, Task::STATE_FINISHED)
    return
  elsif vm.state == Vm::STATE_SUSPENDED
    setTaskState(task, Task::STATE_FAILED, "Cannot save suspended domain")
    return    
  elsif vm.state == Vm::STATE_STOPPED
    setTaskState(task, Task::STATE_FAILED, "Cannot save shutdown domain")
    return
  end

  vm_orig_state = vm.state
  setVmState(vm, Vm::STATE_SAVING)

  begin
    # OK, now that we found the VM, go looking in the hosts table
    begin
      host = findHost(task, vm.host_id)
    rescue
      setTaskState(task, Task::STATE_FAILED, "Could not find the host that VM is running on")
      raise
    end
    
    begin
      conn = Libvirt::open("qemu+tcp://" + host.hostname + "/system")
      dom = conn.lookup_domain_by_uuid(vm.uuid)
      dom.save("/tmp/" + vm.uuid + ".save")
      conn.close
    rescue
      setTaskState(task, Task::STATE_FAILED, "Save failed")
      raise
    end
  rescue
    setVmState(vm, vm_orig_state)
    return
  end

  # note that we do *not* reset the host_id here, since we stored the saved
  # vm state information locally.  restore_vm will pick it up from here

  # FIXME: it would be much nicer to be able to save the VM and remove the
  # the host_id and undefine the XML; that way we could resume it on another
  # host later.  This can be done once we have the storage APIs, but it will
  # need more work

  setTaskState(task, Task::STATE_FINISHED)

  setVmState(vm, Vm::STATE_SAVED)
end

def restore_vm(task)
  puts "restore_vm"

  # here, we are given an id for a VM to start

  begin
    vm = findVM(task)
  rescue
    return
  end

  if vm.state == Vm::STATE_RUNNING
    # the VM is already saved; just return success
    setTaskState(task, Task::STATE_FINISHED)
    return
  elsif vm.state == Vm::STATE_SUSPENDED
    setTaskState(task, Task::STATE_FAILED, "Cannot restore suspended domain")
    return    
  elsif vm.state == Vm::STATE_STOPPED
    setTaskState(task, Task::STATE_FAILED, "Cannot restore shutdown domain")
    return
  end

  vm_orig_state = vm.state
  setVmState(vm, Vm::STATE_RESTORING)

  begin
    # OK, now that we found the VM, go looking in the hosts table
    begin
      host = findHost(task, vm.host_id)
    rescue
      setTaskState(task, Task::STATE_FAILED, "Could not find the host that VM is running on")
      raise
    end
    
    # FIXME: we should probably go out to the host and check what it thinks
    # the state is
    
    begin
      conn = Libvirt::open("qemu+tcp://" + host.hostname + "/system")
      dom = conn.lookup_domain_by_uuid(vm.uuid)
      dom.restore
      conn.close
    rescue
      # FIXME: these may fail for various reasons:
      # 1.  The domain is already defined and/or started - update the DB
      # 2.  We couldn't define the domain for some reason
      setTaskState(task, Task::STATE_FAILED, "Libvirt error")
      raise
    end
  rescue
    setVmState(vm, vm_orig_state)
    return
  end

  setTaskState(task, Task::STATE_FINISHED)

  setVmState(vm, Vm::STATE_RUNNING)
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

  if vm.state == Vm::STATE_SUSPENDED
    # the VM is already suspended; just return success
    setTaskState(task, Task::STATE_FINISHED)
    return
  elsif vm.state == Vm::STATE_STOPPED
    setTaskState(task, Task::STATE_FAILED, "Cannot suspend stopped domain")
    return
  elsif vm.state == Vm::STATE_SAVED
    setTaskState(task, Task::STATE_FAILED, "Cannot suspend saved domain")
    return
  end

  vm_orig_state = vm.state
  setVmState(vm, Vm::STATE_SUSPENDING)

  begin
    # OK, now that we found the VM, go looking in the hosts table
    begin
      host = findHost(task, vm.host_id)
    rescue
      setTaskState(task, Task::STATE_FAILED, "Could not find the host that VM is running on")
      raise
    end
    
    begin
      conn = Libvirt::open("qemu+tcp://" + host.hostname + "/system")
      dom = conn.lookup_domain_by_uuid(vm.uuid)
      dom.suspend
      conn.close
    rescue
      setTaskState(task, Task::STATE_FAILED, "Error looking up domain " + vm.uuid)
      raise
    end
  rescue
    setVmState(vm, vm_orig_state)
    return
  end

  # note that we do *not* reset the host_id here, since we just suspended the VM
  # resume_vm will pick it up from here

  setTaskState(task, Task::STATE_FINISHED)

  setVmState(vm, Vm::STATE_SUSPENDED)
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

  if vm.state == Vm::STATE_RUNNING
    # the VM is already suspended; just return success
    setTaskState(task, Task::STATE_FINISHED)
    return
  elsif vm.state == Vm::STATE_STOPPED
    setTaskState(task, Task::STATE_FAILED, "Cannot resume stopped domain")
    return
  elsif vm.state == Vm::STATE_SAVED
    setTaskState(task, Task::STATE_FAILED, "Cannot resume suspended domain")
    return
  end

  vm_orig_state = vm.state
  setVmState(vm, Vm::STATE_RESUMING)

  begin
    # OK, now that we found the VM, go looking in the hosts table
    begin
      host = findHost(task, vm.host_id)
    rescue
      setTaskState(task, Task::STATE_FAILED, "Could not find the host that VM is running on")
      raise
    end
    
    begin
      conn = Libvirt::open("qemu+tcp://" + host.hostname + "/system")
      dom = conn.lookup_domain_by_uuid(vm.uuid)
      dom.resume
      conn.close
    rescue
      setTaskState(task, Task::STATE_FAILED, "Error looking up domain " + vm.uuid)
      raise
    end
  rescue
    setVmState(vm, vm_orig_state)
    return
  end

  setTaskState(task, Task::STATE_FINISHED)
  
  setVmState(vm, Vm::STATE_RUNNING)
end

def update_state_vm(task)
  puts "update_state_vm"

  # NOTE: findVM() will only return a vm if all the host information is filled
  # in.  So if a vm that we thought was stopped is running, this returns nil
  # and we don't update any information about it.  The tricky part
  # is that we're still not sure what to do in this case :).  - Ian
  begin
    vm = findVM(task)
  rescue
    return
  end

  vm_effective_state = Vm::EFFECTIVE_STATE[vm.state]
  task_effective_state = Vm::EFFECTIVE_STATE[task.args]

  if vm_effective_state != task_effective_state
    vm.state = task.args

    if task_effective_state == Vm::STATE_STOPPED
      vm.host_id = nil
      vm.memory_used = nil
      vm.num_vcpus_used = nil
      vm.needs_restart = nil
      vm.host_id = nil
    end
    vm.save
    msg = "Updated state to " + task.args
  else
    msg = nil
  end

  setTaskState(task, Task::STATE_FINISHED, msg)
end
