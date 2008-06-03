# 
# Copyright (C) 2008 Red Hat, Inc.
# Written by Scott Seago <sseago@redhat.com>
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

class DashboardController < ApplicationController
  def index
    @default_pool = HardwarePool.get_default_pool
    set_perms(@default_pool)
    #remove these soon
    @hardware_pools = HardwarePool.find(:all)
    @available_hosts = Host.find(:all)
    @available_storage_volumes = StorageVolume.find(:all)
    @storage_pools = StoragePool.find(:all)
    @hosts = Host.find(:all)
    @storage_volumes = StorageVolume.find(:all)
    @vms = Vm.find(:all)
    if params[:ajax]
      render :layout => 'tabs-and-content' #:template => 'hardware/show.html.erb'
    end
  end
end
