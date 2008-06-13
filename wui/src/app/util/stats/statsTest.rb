#!/usr/bin/ruby
# 
# Copyright (C) 2008 Red Hat, Inc.
# Written by Mark Wagner <mwagner@redhat.com>
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

#  
#  This is a test program for the ovirt statistical data retrieval
#  It shows some simple steps to build a request list and then 
#  request and process the data.
  
require 'util/stats/Stats'

#  Retrieve the "idle" data for cpu0 from node3, node4, and node5
 
   requestList = []
#   requestList << StatsRequest.new("node3.priv.ovirt.org", DevClass::Load, 0, LoadCounter::Load_1min, 0, 3600, 10 )
#   requestList << StatsRequest.new("node3.priv.ovirt.org", DevClass::Load, 0, LoadCounter::Load_1min, 0, 0, RRDResolution::Long )
#   requestList << StatsRequest.new("node3.priv.ovirt.org", DevClass::Load, 0, LoadCounter::Load_15min, 0, 0, RRDResolution::Long )
#   requestList << StatsRequest.new("node7.priv.ovirt.org", DevClass::NIC, 0, NicCounter::Octets_rx, 0, 0, RRDResolution::Long )
#   requestList << StatsRequest.new("node3.priv.ovirt.org", DevClass::NIC, 1, NicCounter::Octets_rx, 0, 0, RRDResolution::Long )
   requestList << StatsRequest.new("node3.priv.ovirt.org", DevClass::NIC, 0, NicCounter::Octets_tx, 0, 604800, RRDResolution::Medium )
#   requestList << StatsRequest.new("node3.priv.ovirt.org", DevClass::Disk, 0, DiskCounter::Octets_read, 0, 0, RRDResolution::Long )
#   requestList << StatsRequest.new("node3.priv.ovirt.org", DevClass::Disk, 0, DiskCounter::Octets_write, 0, 0, RRDResolution::Long )
#   requestList << StatsRequest.new("node3.priv.ovirt.org", "cpu", 0, "idle", 1211688000, 3600, 10 )
#   requestList << StatsRequest.new("node4.priv.ovirt.org", DevClass::CPU, 0, CpuCounter::Idle, 0, 3600, RRDResolution::Short )
#   requestList << StatsRequest.new("node5.priv.ovirt.org", "cpu", 0, "idle", 1211688000, 3600, 500 )
#   requestList << StatsRequest.new("node5.priv.ovirt.org", DevClass::Memory, 0, MemCounter::Used, 0, 3600, 10 )

   #  Now send the request list and store the results in the statsList.
   statsListBig = getStatsData?( requestList )
   tmp = ""

   #  Now lets loop through the list, pull off the statsData object and get the data from it. 
   #  Note that there is currently only one list sent back, so you need to check the node, 
   #  device and counter for each to detect changes.  We can look at using a list of lists 
   #  if you think it is easier to process the results. 

# puts statsListBig.length
   statsListBig.each do |statsList|
   myNodeName = statsList.get_node?()
   myDevClass = statsList.get_devClass?()
   myInstance = statsList.get_instance?()
   myCounter = statsList.get_counter?()
   myStatus = statsList.get_status?()

   case myStatus
      when StatsStatus::E_NOSUCHNODE
          puts "Can't find data for node " + myNodeName
      when StatsStatus::E_UNKNOWN
          puts "Can't find data for requested file path"
   end
      if tmp != myNodeName then
         puts
      end
   list = statsList.get_data?()
   list.each do |d|
      print("\t", myNodeName, "\t", myDevClass, "\t", myInstance, "\t",  myCounter, "\t",d.get_value?, "\t",d.get_timestamp?)
      puts
   end  
      tmp = myNodeName
   end  


