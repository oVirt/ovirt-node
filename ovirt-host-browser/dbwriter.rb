#!/usr/bin/ruby

require 'active_record'
require 'erb'
require '../wui/src/app/models/host.rb'

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

#ActiveRecord::Base.connection.execute("SELECT * from hosts")

Host.new(
	"uuid" => ARGV[0],
	"num_cpus" => ARGV[1],
	"cpu_speed" => ARGV[2],
	"arch" => ARGV[3],
	"memory" => ARGV[4]
).save
