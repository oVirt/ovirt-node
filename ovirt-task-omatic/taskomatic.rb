#!/usr/bin/ruby

require 'active_record'
require 'erb'

#require '../wui/src/app/models/task.rb'
require 'task.rb'

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

while(true)
  puts 'Checking for tasks...'

  Task.find(:all).each do |task|
    puts task
    puts task.user_id
    puts task.action_type
    task.destroy
  end

  sleep 5
end
