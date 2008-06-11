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

#define class StatsData  List
class StatsDataList
  def initialize(node,devClass,instance, counter, status, function)
    # Instance variables  
    @node = node
    @devClass = devClass
    @instance = instance
    @counter = counter
    @data=[]
    @status = status
    @function = function
  end  
  
  def get_node?()  
    return @node
  end  
  
  def get_devClass?()  
    return @devClass
  end  
  
  def get_instance?()  
    return @instance
  end  
  
  def get_counter?()  
    return @counter
  end  
  
  def get_data?()  
    return @data
  end  
  
  def get_status?()  
    return @status
  end  
  
  def get_function?()  
    return @function
  end  
  
  def append_data(incoming)  
    @data << incoming
  end  
  
  def length()
    return @data.length
   end
end  
