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

$: << File.join(File.dirname(__FILE__), "../dutils")

require 'rubygems'
require 'libvirt'
require 'dutils'

if ARGV.length != 1
  exit
end

# connects to the db in here
require 'dutils'

# make sure we get our credentials up-front
get_credentials

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
           "hardware_pool" => HardwarePool.get_default_pool
           ).save
end
