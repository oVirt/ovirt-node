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
require 'util/stats/StatsTypes'
require 'util/stats/StatsData'
require 'util/stats/StatsDataList'
require 'util/stats/StatsRequest'

def fetchData?(node, devClass, instance, counter, startTime, duration, interval)

   if (interval == 0)
      interval = RRDResolution::Default
   end

   if (startTime == 0)
      if (duration > 0 )
         sTime = Time.now.to_i - duration
      else
         sTime = Time.now.to_i - 86400 
      end
      eTime = Time.now.to_i  
   else
      sTime = startTime
      eTime = sTime + duration
   end 

   # Now mangle based on the intervals

   start =  (sTime / interval).to_i * interval 
   endTime =  (eTime / interval).to_i * interval 
   rrdBase="/var/lib/collectd/rrd/"
   rrdNode=rrdBase + node + "/"

   # Now we need to mess a bit to get the right combos
   case devClass
    when DevClass::CPU
       rrdTail = CpuCounter.getRRDPath(instance, counter)
       lIndex = CpuCounter.getRRDIndex(counter)
    when DevClass::Memory
       rrdTail = MemCounter.getRRDPath(instance, counter)
       lIndex = MemCounter.getRRDIndex(counter)
    when DevClass::Load
       rrdTail = LoadCounter.getRRDPath(instance, counter)
       lIndex = LoadCounter.getRRDIndex(counter)
    when DevClass::NIC
       rrdTail = NicCounter.getRRDPath(instance, counter)
       lIndex = NicCounter.getRRDIndex(counter)
    when DevClass::Disk
       rrdTail = DiskCounter.getRRDPath(instance, counter)
       lIndex = DiskCounter.getRRDIndex(counter)
    else
       puts "Nothing for devClass"
    end

    rrd = rrdNode + rrdTail + ".rrd"

    if ( File.exists?(rrd ) )
       localStatus = StatsStatus::SUCCESS
    elsif ( File.exists?(rrdNode ))
       # Check the Node first
       localStatus = StatsStatus::E_NOSUCHNODE
    else
       # Currently can't distinguish between device and counter, so return generic error 
       localStatus = StatsStatus::E_UNKNOWN
   end
   
   returnList = StatsDataList.new(node,devClass,instance, counter, localStatus)
   
   # So if the path is bad, no need to continue, it will just thrown an error, just return

   if ( localStatus == StatsStatus::SUCCESS )
      (fstart, fend, names, data, interval) = RRD.fetch(rrd, "--start", start.to_s, "--end", endTime.to_s, "AVERAGE", "-r", interval.to_s)
      i = 0 
      # For some reason, we get an extra datapoint at the end.  Just chop it off now...
      data.delete_at(-1)

      # Now, lets walk the returned data and create the ojects, and put them in a list.
      data.each do |vdata|
         i += 1
         returnList.append_data( StatsData.new(fstart + interval * i, vdata[lIndex] ))
      end
   end
   
 return returnList
end




def  getStatsData?(statRequestList)
    tmpList = []
    
    myList = []
    statRequestList.each do |request|
       node = request.get_node?
       counter = request.get_counter?
          tmpList =fetchData?(request.get_node?, request.get_devClass?,request.get_instance?, request.get_counter?,request.get_starttime?, request.get_duration?,request.get_precision?)
 
       #  Now copy the array returned into the main array
       myList << tmpList
    end

return myList

end
