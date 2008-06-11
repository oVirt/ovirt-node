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

# This is the base level request mechanism for the ovirt statistical
# interface

require 'util/stats/StatsTypes'

#define class StatsRequest  
class StatsRequest  
  def initialize(node, devClass, instance, counter, starttime, duration, precision, function=0)  
    # Instance variables  
    @node = node
    @devClass = devClass
    @instance = instance
    @counter = counter
    @starttime = starttime
    @duration = duration
    @precision = precision
    @function = function
  end  
  
  def get_node?()  
    return @node
  end  
  
  def get_counter?()  
    return @counter
  end  
  
  def get_devClass?()  
    return @devClass
  end  
  
  def get_instance?()  
    return @instance
  end  
  
  def get_starttime?()  
    return @starttime
  end  
  
  def get_duration?()  
    return @duration
  end  
  
  def get_precision?()  
    return @precision
  end  
  
  def get_function?()  
    return @function
  end  
end  
