#!/usr/bin/ruby

$: << "../app"
$: << "/usr/share/ovirt-wui/app"

require 'rubygems'
require 'kerberos'
include Kerberos
require 'libvirt'
require 'active_record'
require 'erb'
require 'models/host.rb'
require 'models/hardware_pool.rb'
require 'models/permission.rb'
require 'models/motor_pool.rb'

ENV['KRB5CCNAME'] = '/usr/share/ovirt-wui/ovirt-cc'

def database_configuration
  YAML::load(ERB.new(IO.read('/usr/share/ovirt-wui/config/database.yml')).result)
end

if ARGV.length != 1
  exit
end

# make sure we get our credentials up-front
krb5 = Krb5.new
default_realm = krb5.get_default_realm
krb5.get_init_creds_keytab('libvirt/' + Socket::gethostname + '@' + default_realm, '/usr/share/ovirt-wui/ovirt.keytab')
krb5.cache(ENV['KRB5CCNAME'])

begin
  conn = Libvirt::open("qemu+tcp://" + ARGV[0] + "/system")
  info = conn.node_get_info
  conn.close
rescue
  # if we can't contact the host or get details for some reason, we just
  # don't do anything and don't add anything to the database
  puts "Failed connecting to host " + ARGV[0]
  exit
end

# we could destroy the credentials, but another process might be using them
# (in particular, the taskomatic).  Just leave them around, it shouldn't hurt

$dbconfig = database_configuration

$develdb = $dbconfig['development']

ActiveRecord::Base.establish_connection(
                                        :adapter  => $develdb['adapter'],
                                        :host     => $develdb['host'],
                                        :username => $develdb['username'],
                                        :password => $develdb['password'],
                                        :database => $develdb['database']
                                        )

# FIXME: we need a better way to get a UUID, rather than the hostname
$host = Host.find(:first, :conditions => [ "uuid = ?", ARGV[0]])

if $host == nil
  Host.new(
           "uuid" => ARGV[0],
           "hostname" => ARGV[0],
           "num_cpus" => info.cpus,
           "cpu_speed" => info.mhz,
           "arch" => info.model,
           "memory" => info.memory,
           "is_disabled" => 0,
           "hardware_pool" => MotorPool.find(:first)
           ).save
end
