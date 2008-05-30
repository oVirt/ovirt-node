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
  
require 'Stats'

#  Retrieve the "idle" data for cpu0 from node3, node4, and node5
 
   requestList = []
   requestList << StatsRequest.new("node3", "cpu", 0, "idle", 1211688000, 3600, 10 )
   requestList << StatsRequest.new("node4", "cpu", 0, "idle", 0, 3600, 10 )
   requestList << StatsRequest.new("node5", "cpu", 0, "idle", 1211688000, 3600, 500 )
   requestList << StatsRequest.new("node5", "memory", 0, "used", 0, 3600, 0 )

   #  Now send the request list and store the results in the statsList.
   statsListBig = getStatsData?( requestList )
   tmp = ""

   #  Now lets loop through the returned list. It is a list of lists so take the first list 
   # and chomp through it. 
   #, pull off the statsData object and get the data from it. 

   statsListBig.each do |statsList|
      # grab the data about this list, this will be consistent for all StatData objects in this list.
      myNodeName = statsList.get_node?()
      myDevClass = statsList.get_devClass?()
      myInstance = statsList.get_instance?()
      myCounter = statsList.get_counter?()

      # add a newline to break up data from different nodes for readability
      if tmp != myNodeName then
         puts
      end
      #  Now grab the data that is stored in the list
      #  and loop through it.  Note that we print it our directly

      list = statsList.get_data?()
      list.each do |d|
         print("\t", myNodeName, "\t", myDevClass, "\t", myInstance, "\t",  myCounter, "\t",d.get_value?, "\t",d.get_timestamp?)
         puts
      end  
      tmp = myNodeName
   end  


