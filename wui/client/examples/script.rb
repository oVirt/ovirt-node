#! /usr/bin/ruby

# Sample script that shows how to use the OVirt API

require 'pp'
require 'rubygems'
require 'activeresource'
require 'optparse'

require 'ovirt'

def move_random_host(hosts, pool)
    host = hosts[rand(hosts.size)]
    puts "Move #{host.hostname} to #{pool.name}"
    pool.hosts << host
    pool.save
end

def element_path(obj)
    "[#{obj.class.element_path(obj.id)}]"
end

def print_pool(pool)
    puts "\n\nPool #{pool.name}: #{pool.hosts.size} hosts, #{pool.storage_pools.size} storage pools #{element_path(pool)} "
    puts "=" * 75
    pool.hosts.each do |h|
        printf "%-36s %s\n", h.hostname, element_path(h)
    end
    pool.storage_pools.each do |sp|
        type = sp.nfs? ? "NFS" : "iSCSI"
        printf "%-5s %-30s %s\n", type, sp.label, element_path(sp)
    end
    puts "-" * 75
end

# Plumbing so we can find the OVirt server
# "http://ovirt.watzmann.net:3000/ovirt/rest"
PROGNAME=File::basename($0)
OVirt::Base.site = ENV["OVIRT_SERVER"]
opts = OptionParser.new("#{PROGNAME} GLOBAL_OPTS")
opts.separator("  Run some things against an OVirt server. The server is specified with")
opts.separator("  the -s option as a URL of the form http://USER:PASSWORD@SERVER/ovirt")
opts.separator("")
opts.separator "Global options:"
opts.on("-s", "--server=URL", "The OVirt server. Since there is no auth\n" +
        "#{" "*37}yet, must be the mongrel server port.\n" +
        "#{" "*37}Overrides env var OVIRT_SERVER") do |val|
    OVirt::Base.site = val
end

opts.order(ARGV)

unless OVirt::Base.site
    $stderr.puts <<EOF
You must specify the OVirt server to connect to, either with the
--server option or through the OVIRT_SERVER environment variable
EOF
    exit 1
end

OVirt::Base.login

# Get a single host by name
host = OVirt::Host.find_by_hostname("node3.priv.ovirt.org")
puts "#{host.uuid} has id #{host.id}"

# What's in the default pool
defpool = OVirt::HardwarePool.default_pool
print_pool(defpool)

# Create a new hardware pool
mypool = OVirt::HardwarePool.find_by_path("/default/mypool")
unless mypool
    puts "Create mypool"
    mypool = OVirt::HardwarePool.create( { :parent_id => defpool.id,
                                             :name => "mypool" } )
end

# Move some hosts around
puts
if defpool.hosts.size > 1
    move_random_host(defpool.hosts, mypool)
elsif mypool.hosts.size > 0
    move_random_host(mypool.hosts, defpool)
end

# Delete all storage pools for mypool and add a new one
mypool.storage_pools.each do |sp|
    puts "Delete storage pool #{sp.id}"
    sp.destroy
end

storage_pool = OVirt::StoragePool.create( { :storage_type => "NFS",
                                            :hardware_pool_id => mypool.id,
                                            :ip_addr => "192.168.122.50",
                                            :export_path => "/exports/pool1" } )
puts "Created storage pool #{storage_pool.id}"

# For some reason, mypool.reload doesn't work here
mypool = OVirt::HardwarePool.find_by_path("/default/mypool")
print_pool(mypool)
