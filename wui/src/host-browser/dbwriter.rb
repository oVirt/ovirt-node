#!/usr/bin/ruby

$: << "../app"
$: << "/usr/share/invirt-wui/app"

require 'rubygems'
require 'active_record'
require 'erb'
require 'models/host.rb'
require 'models/hardware_resource_group.rb'

def database_configuration
  YAML::load(ERB.new(IO.read('/usr/share/invirt-wui/config/database.yml')).result)
end

if ARGV.length != 5
  exit
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

# FIXME: we need a better way to get a UUID, rather than the hostname
$host = Host.find(:first, :conditions => [ "uuid = ?", ARGV[0]])

if $host == nil
  Host.new(
           "uuid" => ARGV[0],
           "hostname" => ARGV[0],
           "num_cpus" => ARGV[1],
           "cpu_speed" => ARGV[2],
           "arch" => ARGV[3],
           "memory" => ARGV[4],
           "is_disabled" => 0,
           "hardware_resource_group" => HardwareResourceGroup.get_default_group
           ).save

end
