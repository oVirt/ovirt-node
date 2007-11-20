#!/usr/bin/ruby

require 'active_record'
require 'erb'
require 'libvirt'

require '../wui/src/app/models/task.rb'
require '../wui/src/app/models/host.rb'
require '../wui/src/app/models/vm.rb'

def database_configuration
  YAML::load(ERB.new(IO.read('../wui/src/config/database.yml')).result)
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

  # first, find the matching VM in the vms table
  vm = Vm.find(:first, :conditions => [ "uuid = ?", task.vm_id ])

  if vm == nil
    puts "No VM found"
    return
  end

  puts vm

  # FIXME: error checking; make sure that the VM wasn't already created

  # OK, now that we found the VM, go looking in the hosts table to see if there
  # is a host that will fit these constraints
  host = Host.find(:first, :conditions => [ "num_cpus >= ? AND memory >= ?", vm.num_vcpus_allocated, vm.memory_allocated])
  puts host

  # FIXME: error checking; if we didn't find a host, report an error

  # OK, we found a host we can do this on.  Build up the XML for libvirt
  conn = Libvirt::open("qemu+tls://" + host.hostname + "/system")

  if conn == nil
    puts "Failed connecting to ovirt host " + host.hostname
    # FIXME: we probably want to loop around and try another host here
    return
  end

  # FIXME: probably want to Libvirt::lookupDomainByUUID here to check if it
  # is already running

  # FIXME: do we want to createDomainLinux or defineDomainXML?

  conn.close

end

def shutdown_vm(task)
  puts "start_vm"
  puts task
  puts task.vm_id

  # here, we are given a UUID for a VM to shutdown; we have to lookup which
  # physical host it is running on

  # first, find the matching VM in the vms table
  vm = Vm.find(:first, :conditions => [ "uuid = ?", task.vm_id ])
  
  if vm == nil
    puts "No VM found"
    return    
  end

  # FIXME: error checking; check that this vm is in a state we understand
  # (basically, that it is not running already)

  # OK, now that we found the VM, go looking in the hosts table to see if there
  # is a host that will fit these constraints
  host = Host.find(:first, :conditions => [ "num_cpus >= ? AND memory >= ?", vm.num_vcpus_allocated, vm.memory_allocated])
  puts host

  # FIXME: error checking; what if no host fits this?

  conn = Libvirt::open("qemu+tls://" + host.hostname + "/system")

  dom = conn.lookupDomainByUUID(vm.uuid)

  dom.shutdown()

  conn.close
end

def start_vm(task)
  puts "start_vm"

  # here, we are given an id for a VM to start

  # first, find the matching VM in the vms table
  vm = Vm.find(:first, :conditions => [ "id = ?", task.vm_id ])
  
  if vm == nil
    puts "No VM found"
    return    
  end

  # FIXME: error checking; check that this vm is in a state we understand
  # (basically, that it is not running already)

  # OK, now that we found the VM, go looking in the hosts table to see if there
  # is a host that will fit these constraints
  host = Host.find(:first, :conditions => [ "num_cpus >= ? AND memory >= ?", vm.num_vcpus_allocated, vm.memory_allocated])
  puts host

  # FIXME: error checking; what if no host fits this?

  conn = Libvirt::open("qemu+tls://" + host.hostname + "/system")

  dom = conn.lookupDomainByUUID(vm.uuid)

  dom.create()

  conn.close
end

def suspend_vm(task)
end

def resume_vm(task)
end

while(true)
  puts 'Checking for tasks...'

  Task.find(:all).each do |task|
    case task.action
      when "create_vm" then create_vm(task)
      when "shutdown_vm" then shutdown_vm(task)
      when "start_vm" then start_vm(task)
      when "suspend_vm" then suspend_vm(task)
      when "resume_vm" then resume_vm(task)
      else puts "unknown"
    end

    # FIXME: do we really want to do this?  How do we report errors?
    #task.destroy
  end

  sleep 5
end
