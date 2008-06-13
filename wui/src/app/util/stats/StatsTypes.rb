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


class DevClass 
   def DevClass.add_item(key,value)
      @hash ||= {}  
      @hash[key]=value
   end       
         
   def DevClass.const_missing(key)
      @hash[key]    
   end       
         
   def DevClass.each
      @hash.each {|key,value| yield(key,value)}
   end       
         
   def DevClass.getRRDDevName?(key)
      return @hash.values_at(key)
   end


   DevClass.add_item :CPU, 1
   DevClass.add_item :Memory, 2
   DevClass.add_item :Disk, 3
   DevClass.add_item :Load, 4
   DevClass.add_item :NIC, 5
end   
       

class DiskCounter
   def DiskCounter.add_item(key,value)
      @hash ||= {}
      @hash[key]=value
   end

   def DiskCounter.const_missing(key)
      @hash[key]
   end

   def DiskCounter.each
      @hash.each {|key,value| yield(key,value)}
   end

   def  DiskCounter.getRRDPath(instance, counter)
        extension = ".rrd"
        path = "disk-dm-" + instance.to_s + "/"
        case counter
           when DiskCounter::Merged_read,  DiskCounter::Merged_write
              path += "disk_merged"
           when DiskCounter::Octets_read,  DiskCounter::Octets_write
              path += "disk_octets"
           when DiskCounter::Ops_read,  DiskCounter::Ops_write
              path += "disk_ops"
           when DiskCounter::Time_read,  DiskCounter::Time_write
              path += "disk_time"
           else
              puts "Nothing"
           end

        return path
   end
   def DiskCounter.getRRDIndex(counter)
        case counter
           when DiskCounter::Merged_read, DiskCounter::Octets_read, DiskCounter::Ops_read,  DiskCounter::Time_read
              localIndex = 0
           when DiskCounter::Merged_read, DiskCounter::Octets_write, DiskCounter::Ops_write,  DiskCounter::Time_write
              localIndex = 1
           else
              localIndex = 0
           end

        return localIndex
   end

   DiskCounter.add_item :Merged_read, 1
   DiskCounter.add_item :Merged_write, 2
   DiskCounter.add_item :Octets_read, 3
   DiskCounter.add_item :Octets_write, 4
   DiskCounter.add_item :Ops_read, 5
   DiskCounter.add_item :Ops_write, 6
   DiskCounter.add_item :Time_read, 7
   DiskCounter.add_item :Time_write, 8
end

class CpuCounter
   def CpuCounter.add_item(key,value)
      @hash ||= {}  
      @hash[key]=value
   end       
         
   def CpuCounter.const_missing(key)
      @hash[key]    
   end       
         
   def CpuCounter.each
      @hash.each {|key,value| yield(key,value)}
   end       
         
   def  CpuCounter.getRRDPath(instance, counter)
        extension = ".rrd"
        path = "cpu-" + instance.to_s + "/cpu-"
        case counter
           when CpuCounter::Idle
              path += "idle"
           when CpuCounter::CalcUsed
              path += "idle"
           when CpuCounter::Interrupt
              path += "interrupt"
           when CpuCounter::Nice
              path += "nice"
           when CpuCounter::Softirq
              path += "softirq"
           when CpuCounter::Steal
              path += "steal"
           when CpuCounter::System
              path += "system"
           when CpuCounter::User
              path += "user"
           when CpuCounter::Wait
              path += "wait"
           else
              puts "Nothing"
           end
          
        return path
   end


   def CpuCounter.getRRDIndex(counter)
        return 0
   end


   CpuCounter.add_item :Idle, 1
   CpuCounter.add_item :Interrupt, 2
   CpuCounter.add_item :Nice, 3
   CpuCounter.add_item :Softirq, 4
   CpuCounter.add_item :Steal, 5
   CpuCounter.add_item :System, 6
   CpuCounter.add_item :User, 7
   CpuCounter.add_item :Wait, 8
   CpuCounter.add_item :CalcUsed, 8
end   
       
class MemCounter
   def MemCounter.add_item(key,value)
      @hash ||= {}  
      @hash[key]=value
   end       
         
   def MemCounter.const_missing(key)
      @hash[key]    
   end       
         
   def MemCounter.each
      @hash.each {|key,value| yield(key,value)}
   end       
         
   def  MemCounter.getRRDPath(instance, counter)
        path = "memory/memory-"
        case counter
           when MemCounter::Buffered
              path += "buffered"
           when CpuCounter::Cached
              path += "cache"
           when MemCounter::Free
              path += "free"
           when MemCounter::Used
              path += "used"
           else
              puts "Nothing"
           end
        return path
   end

   def MemCounter.getRRDIndex(counter)
        return 0
   end


   MemCounter.add_item :Buffered, 1
   MemCounter.add_item :Cached, 2
   MemCounter.add_item :Free, 3
   MemCounter.add_item :Used, 4
end   
       
class NicCounter
   def NicCounter.add_item(key,value)
      @hash ||= {}  
      @hash[key]=value
   end       
         
   def NicCounter.const_missing(key)
      @hash[key]    
   end       
         
   def NicCounter.each
      @hash.each {|key,value| yield(key,value)}
   end       

   def  NicCounter.getRRDPath(instance, counter)
        extension = ".rrd"
        path = "interface/"
        case counter
           when NicCounter::Errors_rx,  NicCounter::Errors_tx
              path += "if_errors-eth" + instance.to_s
           when NicCounter::Octets_rx,  NicCounter::Octets_tx
              path += "if_octets-eth" + instance.to_s
           when NicCounter::Packets_rx,  NicCounter::Packets_tx
              path += "if_packets-eth" + instance.to_s
           else
              puts "Nothing"
           end

        return path
   end

   def NicCounter.getRRDIndex(counter)
        case counter
           when NicCounter::Errors_rx
              localIndex = 0
           when NicCounter::Errors_tx
              localIndex = 1
           when NicCounter::Octets_rx
              localIndex = 0
           when NicCounter::Octets_tx
              localIndex = 1
           when NicCounter::Packets_rx
              localIndex = 0
           when NicCounter::Packets_tx
              localIndex = 1
           else
              localIndex = 0
           end

        return localIndex
   end
 
         
   NicCounter.add_item :Errors_rx, 1
   NicCounter.add_item :Errors_tx, 2
   NicCounter.add_item :Octets_rx, 3
   NicCounter.add_item :Octets_tx, 4
   NicCounter.add_item :Packets_rx, 5
   NicCounter.add_item :Packets_tx, 6
end   
       
class LoadCounter
   def LoadCounter.add_item(key,value)
      @hash ||= {}  
      @hash[key]=value
   end       
         
   def LoadCounter.const_missing(key)
      @hash[key]    
   end       
         
   def LoadCounter.each
      @hash.each {|key,value| yield(key,value)}
   end       
         
   def  LoadCounter.getRRDPath(instance, counter)
        path = "load/"
        case counter
           when LoadCounter::Load_1min, LoadCounter::Load_5min, LoadCounter::Load_15min
              path += "load"
           else
              puts "Nothing"
           end
        return path
   end

   def LoadCounter.getRRDIndex(counter)
      case counter
         when LoadCounter::Load_1min
            localIndex = 0
         when LoadCounter::Load_5min
            localIndex = 1
         when LoadCounter::Load_15min
            localIndex = 2
         else
            localIndex = 0
      end

      return localIndex
   end

   LoadCounter.add_item :Load_1min, 1
   LoadCounter.add_item :Load_5min, 5
   LoadCounter.add_item :Load_15min, 15
end   

class RRDResolution
   def RRDResolution.add_item(key,value)
      @hash ||= {}
      @hash[key]=value
   end

   def RRDResolution.const_missing(key)
      @hash[key]
   end

   def RRDResolution.each
      @hash.each {|key,value| yield(key,value)}
   end

   # Set up the resolutions for our rrd
   RRDResolution.add_item :Default, 10    # Ten secs
   RRDResolution.add_item :Short, 500     # 500 secs ( 8minute, 20 sec)
   RRDResolution.add_item :Medium, 2230
   RRDResolution.add_item :Long, 26350
end

       
class StatsStatus
   def StatsStatus.add_item(key,value)
      @hash ||= {}
      @hash[key]=value
   end

   def StatsStatus.const_missing(key)
      @hash[key]
   end

   def StatsStatus.each
      @hash.each {|key,value| yield(key,value)}
   end

   # Set up the resolutions for our rrd
   StatsStatus.add_item :SUCCESS, 0
   StatsStatus.add_item :E_NOSUCHNODE, 1
   StatsStatus.add_item :E_NOSUCHDEVICE, 2
   StatsStatus.add_item :E_NOSUCHCOUNTER, 3
   StatsStatus.add_item :E_UNKNOWN, 99

end
 
#
#  A class to handle the data type, 
#
class DataFunction
   def DataFunction.add_item(key,value)
      @hash ||= {}
      @hash[key]=value
   end

   def DataFunction.const_missing(key)
      @hash[key]
   end

   def DataFunction.each
      @hash.each {|key,value| yield(key,value)}
   end

   # Set up the resolutions for our rrd
   DataFunction.add_item :Average,0
   DataFunction.add_item :Peak,1
   DataFunction.add_item :Min,2
   DataFunction.add_item :RollingAverage,3
   DataFunction.add_item :RollingPeak,4
   DataFunction.add_item :RollingMin,5
end

