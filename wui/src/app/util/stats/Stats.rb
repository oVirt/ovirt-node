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

require 'RRD'
require 'util/stats/StatsTypes'
require 'util/stats/StatsData'
require 'util/stats/StatsDataList'
require 'util/stats/StatsRequest'


# This fetches a rolling average, basically average points before and after.

def fetchRollingAve?(rrdPath, start, endTime, interval, myFunction, lIndex, returnList, aveLen=7)
   final = 0

   #  OK, first thing we need to do is to move the start time back in order to 
   #  have data to average.
       
   indexOffset = ( aveLen / 2 ).to_i
   start -= ( interval  * indexOffset)

   (fstart, fend, names, data, interval) = RRD.fetch(rrdPath, "--start", start.to_s, \
                             "--end", endTime.to_s, myFunction, "-r", interval.to_s)
   i = 0
   # For some reason, we get an extra datapoint at the end.  Just chop it off now...
   data.delete_at(-1)

   # OK, to support callable average lengths, lets use an array
   #  Ruby lets you do some nice things (did I just say that ?) 
   # to manipulate the array so exploit it
 
   roll = []

   # Now, lets walk the returned data and create the objects, and put them in a list.
   data.each do |vdata|
      i += 1
      final = 0
      value = 0
      value = vdata[lIndex]
      value = 0 if value.nan?
 

      roll.push(value)
      if ( i >= aveLen)
         #  OK, now we need to walk the array and sum the values
         # then divide by the length and stick it in the list
         roll.each do |rdata|
            final += rdata
         end
         final = (final / aveLen )
         returnList.append_data( StatsData.new(fstart + interval * ( i - indexOffset), final ))
 
         # Now shift the head off the array
         roll.shift
      end
   end
   
 return returnList
end


def fetchRollingCalcUsedData?(rrdPath, start, endTime, interval, myFunction, lIndex, returnList, aveLen=7)

   # OK, first thing we need to do is to move the start time back in order to have data to average.
      
   indexOffset = ( aveLen / 2 ).to_i
   start -= ( interval  * indexOffset)

   lFunc = "AVERAGE"   
   case myFunction
      when "MAX"
         lFunc="MIN"
      when "MIN"
         lFunc="MAX"
   end

   (fstart, fend, names, data, interval) = RRD.fetch(rrdPath, "--start", start.to_s, \
                             "--end", endTime.to_s, lFunc, "-r", interval.to_s)
   i = 0
   # For some reason, we get an extra datapoint at the end.  Just chop it off now...
   data.delete_at(-1)

   roll = []

   # Now, lets walk the returned data and create the objects, and put them in a list.
   data.each do |vdata|
      i += 1
      final = 0
      value = 0
      value = vdata[lIndex]
      value = 100 if value.nan?
      if ( value > 100 )
         value = 100
      end

      value = 100 - value

      roll.push(value)
      if ( i >= aveLen)
         #  OK, now we need to walk the array and sum the values
         # then divide by the length and stick it in the list
         roll.each do |rdata|
            final += rdata
         end
         final = (final / aveLen)
         returnList.append_data( StatsData.new(fstart + interval * ( i - indexOffset), final ))
         # Now shift the head off the array
         roll.shift
      end
   end

 return returnList
end


def fetchCalcUsedData?(rrdPath, start, endTime, interval, myFunction, lIndex, returnList)

   #  OK, this is a special to massage the data for CPU:CalcUsed
   #  Basically we  take the Idle time and subtract it from 100
   #  We also need to handle NaN differently 
   #  Finally, we need to switch Min and Max
 
   lFunc = "AVERAGE"   
   case myFunction
      when "MAX"
         lFunc="MIN"
      when "MIN"
         lFunc="MAX"
   end

   (fstart, fend, names, data, interval) = RRD.fetch(rrdPath, "--start", start.to_s, \
                                  "--end", endTime.to_s, lFunc, "-r", interval.to_s)
   i = 0 
   # For some reason, we get an extra datapoint at the end.  Just chop it off now...
   data.delete_at(-1)

   # Now, lets walk the returned data and create the ojects, and put them in a list.
   data.each do |vdata|
      i += 1
      value = vdata[lIndex]
         value = 100 if value.nan?
         if ( value > 100 )
            value = 100
         end
         value  =  100 - value
      returnList.append_data( StatsData.new(fstart + interval * i, value ))
   end
   
 return returnList
end


def fetchRegData?(rrdPath, start, endTime, interval, myFunction, lIndex, returnList)

   (fstart, fend, names, data, interval) = RRD.fetch(rrdPath, "--start", start.to_s, "--end", \
                                               endTime.to_s, myFunction, "-r", interval.to_s)
   i = 0 
   # For some reason, we get an extra datapoint at the end.  Just chop it off now...
   data.delete_at(-1)

   # Now, lets walk the returned data and create the ojects, and put them in a list.
   data.each do |vdata|
      i += 1
      returnList.append_data( StatsData.new(fstart + interval * i, vdata[lIndex] ))
   end
   
 return returnList
end


def fetchData?(node, devClass, instance, counter, startTime, duration, interval, function)

   endTime = 0

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
   
    case function
       when DataFunction::Peak 
          myFunction="MAX"
       when DataFunction::Min 
          myFunction="MIN"
       when DataFunction::RollingPeak 
          myFunction="MAX"
       when DataFunction::RollingMin 
          myFunction="MIN"
       else
          myFunction="AVERAGE"
    end

   returnList = StatsDataList.new(node,devClass,instance, counter, localStatus, function)

   if ( localStatus == StatsStatus::SUCCESS )
      if ( function == DataFunction::RollingPeak) || 
         ( function == DataFunction::RollingMin) || 
         ( function == DataFunction::RollingAverage)
         if ( devClass == DevClass::CPU ) && ( counter == CpuCounter::CalcUsed )
            fetchRollingCalcUsedData?(rrd, start, endTime, interval, myFunction, lIndex, returnList)
         else
            fetchRollingAve?(rrd, start, endTime, interval, myFunction, lIndex, returnList)
         end
      else
         if ( devClass == DevClass::CPU ) && ( counter == CpuCounter::CalcUsed )
            fetchCalcUsedData?(rrd, start, endTime, interval, myFunction, lIndex, returnList)
         else
            fetchRegData?(rrd, start, endTime, interval, myFunction, lIndex, returnList)
         end
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
       tmpList =fetchData?(request.get_node?, request.get_devClass?,request.get_instance?, request.get_counter?, \
                     request.get_starttime?, request.get_duration?,request.get_precision?, request.get_function?)
 
       #  Now copy the array returned into the main array
       myList << tmpList
    end

return myList

end
