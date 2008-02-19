#!/usr/bin/ruby
# 
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


$: << "../app"
$: << "/usr/share/ovirt-wui/app"

require 'rubygems'
require 'active_record'
require 'erb'
require 'kerberos'
include Kerberos
require 'libvirt'

require 'models/vm.rb'
require 'models/host.rb'

ENV['KRB5CCNAME'] = '/usr/share/ovirt-wui/ovirt-cc'

$logfile = '/var/log/ovirt-wui/host-status.log'

$stdout = File.new($logfile, 'a')
$stderr = File.new($logfile, 'a')

def database_configuration
  YAML::load(ERB.new(IO.read('/usr/share/ovirt-wui/config/database.yml')).result)
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


def findHost(vm)
  host = Host.find(:first, :conditions => [ "id = ?", vm.host_id])

  if host == nil
    # Hm, we didn't find the host_id.  Seems odd.  Return a failure
    raise
  end

  return host
end

def update_host_list
  vms = Vm.find(:all, :conditions => [ "host_id is NOT NULL" ])
  vms.each do |vm|
    begin
      host = findHost(vm)
    rescue
      # well, we couldn't find the host that this VM is supposedly running on.
      # for now, just skip it
      # FIXME: should we update the database, possibly taking that host
      # 'offline', or whatever?  Really, this shouldn't happen, so it's not
      # a huge deal for now
    end

    if $host_vms.has_key?(host.hostname)
      # we already saw this host (from another VM); don't look at it again
      next
    end
    
    begin
      conn = Libvirt::open("qemu+tcp://" + host.hostname + "/system")
    rescue
      # OK, if we failed to connect for some reason, we just won't monitor this
      # host for now.  It's not a big deal; if this is just a temporary
      # condition, we will pick it up in the next loop
      puts "Can't contact " + host.hostname + "; skipping for now"
      next
    end
    
    defined_domains = conn.list_defined_domains
    
    # FIXME: what happens if defined_domains disagrees with what we have in the
    # database?  This is something *this* daemon is responsible for, so we will
    # have to come up with a way to handle it
    
    dom_states = {}
    defined_domains.each do |domname|
      dom = conn.lookup_domain_by_name(domname)
      info = dom.info
      dom_states[domname] = info.state
    end
    $host_vms[host.hostname] = dom_states

    conn.close
  end
  
  puts $host_vms
end

def get_credentials
  krb5 = Krb5.new
  default_realm = krb5.get_default_realm
  krb5.get_init_creds_keytab('libvirt/' + Socket::gethostname + '@' + default_realm, '/usr/share/ovirt-wui/ovirt.keytab')
  krb5.cache(ENV['KRB5CCNAME'])
end

# here, get an initial list of hosts to monitor.  This is done by looking at
# the running VMs and making a unique list of hosts that that they are running
# on.  In the loop below, the host list will be updated as necessary.
$host_vms = {}
get_credentials
update_host_list

# OK, now we have an initial list.  Let's fork off and check back periodically

pid = fork do
  loop do
    puts "Waking up to check host status..."
    get_credentials
    
    # the first thing to do is to go into the database and check whether we need
    # to update our host list
    update_host_list
    
    $host_vms.keys.each do |host|
      begin
        conn = Libvirt::open("qemu+tcp://" + host + "/system")
      rescue
        # OK, if we failed to connect for some reason, we just won't monitor
        # this host for now.  It's not a big deal; if this is just a temporary
        # condition, we will pick it up in the next loop
        puts "Can't contact " + host + "; skipping for now"
        next
      end
      
      defined_domains = conn.list_defined_domains    
      
      dom_states = {}
      defined_domains.each do |domname|
        dom = conn.lookup_domain_by_name(domname)
        info = dom.info
        dom_states[domname] = info.state
      end
      conn.close
      
      if dom_states === $host_vms[host]
        # here, the domain states are the same as they were last time.  Good, we
        # can go on
        puts "Domain states unchanged on host " + host
        next
      end
      
      # otherwise we need to update both our internal representation of the
      # domain states, as well as the database.  The latter we do through a
      # taskomatic task, since it is the keeper, in the end, of the database
      
      $host_vms[host] = dom_states
      
      # FIXME: implement the taskomatic task!
      
    end
    
    sleep 20
  end
end

Process.detach(pid)
