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

$: << '/usr/lib64/ruby/site_ruby/1.8/x86_64-linux'

require 'RRD'
require 'util/stats/StatsData'
require 'util/stats/StatsDataList'
require 'util/stats/StatsRequest'
require 'util/stats/DummyData' 

def fetchData?(node, devClass, instance, counter, startTime, duration, interval)

   if (interval == 0)
      interval = 10
   end

   if (startTime == 0)
      start = Time.now.to_i - duration
   else
      start = startTime
   end 

   endTime = start + duration

   rrdBase="/var/lib/collectd/rrd/"
   rrdNode=rrdBase + "/" + node + "/"

   # Now we need to mess a bit to get the right combos

   if ( devClass <=> "cpu" ) == 0
       rrdDev = rrdNode + "cpu-" + instance.to_s  
   else
       rrdDev = rrdNode + devClass
   end

   rrd = rrdDev + "/" + devClass + "-" + counter + ".rrd"

   returnList = StatsDataList.new(node,devClass,instance, counter)
   (fstart, fend, names, data, interval) = RRD.fetch(rrd, "--start", start, "--end", endTime, "AVERAGE", "-r", interval)
   i = 0 
   # For some reason, we get an extra datapoint at the end.  Just chop it off now...
   data.delete_at(-1)

   # Now, lets walk the returned data and create the ojects, and put them in a list.
   data.each do |vdata|
      i += 1
      returnList.append_data( StatsData.new(fstart + interval * i, vdata[0] ))
   end
 return returnList
end



#  This is the Ruby entry point into the world of statistics retrieval 
#  for ovirt.


# This call takes a list of StatRequest objects.  
# It returns a list of StatsData objects that contain the data
# that satisifies the request. 
#
# ToDo:
# 1) There is currently no error reporting mechanisms implemented
# 

def  getStatsData?(statRequestList)
    tmpList = []
    myList = []

    statRequestList.each do |request|
       node = request.get_node?
       counter = request.get_counter?
       tmpList =fetchData?(request.get_node?, request.get_devClass?,request.get_instance?, request.get_counter?,request.get_starttime?, request.get_duration?,request.get_precision?)
       myList << tmpList
    end

return myList

end
