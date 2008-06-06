#!/usr/bin/ruby
#
# Copyright (C) 2008 Red Hat, Inc.
# Written by Ian Main <imain@redhat.com>
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

$: << File.join(File.dirname(__FILE__), "../app")
$: << File.join(File.dirname(__FILE__), "../dutils")
$: << File.join(File.dirname(__FILE__), ".")

require 'optparse'
require 'dutils'
require 'models/task'
require 'socket'

do_daemon = true
sleeptime = 30


opts = OptionParser.new do |opts|
  opts.on("-h", "--help", "Print help message") do
    puts opts
    exit
  end
  opts.on("-n", "--nodaemon", "Run interactively (useful for debugging)") do |n|
    do_daemon = !n
  end
  opts.on("-s N", Integer, "--sleep", "Seconds to sleep between iterations (default is 5 seconds)") do |s|
    sleeptime = s
  end
end

begin
  opts.parse!(ARGV)
rescue OptionParser::InvalidOption
  puts opts
  exit
end

if do_daemon
  daemonize
end

f = UNIXSocket.new("/var/lib/collectd/unixsock")

database_connect

loop do
  f.write("LISTVAL\n")

  count = f.gets
  count = count.to_i

  vals = []
  while count > 0 do
    value = f.gets
    vals.push(value)
    count = count - 1
  end

  for val in vals do
    timestamp, keystring = val.split(" ")

    hostname,plugin,type = keystring.split("/")

    if plugin == "load" and type == "load"
      f.write("GETVAL #{keystring}\n")
      valuestring = f.gets

      values = valuestring.split("=")
      if values.length != 4
        puts("GACK! Should have 4 values for load")
        next
      end
      short = values[1].to_f
      med = values[2].to_f
      long = values[3].to_f

      # You only see this in non-daemon mode..
      puts("hostname: #{hostname} --> short: #{short}, med: #{med}, long: #{long}")

      # We have our values now, just need to update the db.
      host = Host.find(:first, :conditions => [ "hostname = ?", hostname])
      if host == nil
        puts("GACK! No such host in database: #{hostname}")
      else
        host.load_average = med
        host.save
      end
    end
  end

  sleep sleeptime

end

