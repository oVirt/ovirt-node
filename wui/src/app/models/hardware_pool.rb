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

class HardwarePool < ActiveRecord::Base

  # overloading this method such that we can use permissions.admins to get all the admins for an object
  has_many :permissions, :dependent => :destroy, :order => "id ASC" do
      def admins
          find_all_by_privilege(Permission::ADMIN)
      end
      def monitors
          find_all_by_privilege(Permission::MONITOR)
      end
      def delegates
          find_all_by_privilege(Permission::DELEGATE)
      end
  end

  has_many :hosts, :dependent => :nullify, :order => "id ASC" do
    def total_cpus
      find(:all).inject(0){ |sum, host| sum + host.num_cpus }
    end
  end

  has_many :storage_pools, :dependent => :nullify, :order => "id ASC" do
    def total_size_in_gb
      find(:all).inject(0){ |sum, sp| sum + sp.storage_volumes.total_size_in_gb }
    end
  end

  belongs_to :superpool, :class_name => "HardwarePool", :foreign_key => "superpool_id"
#  has_many :subpools, :class_name => "HardwarePool", :foreign_key => "superpool_id", :dependent => :nullify, :order => "id ASC"

  def self.list_for_user(user)
    find(:all, :include => "permissions", 
         :conditions => "permissions.user='#{user}' and permissions.privilege='#{Permission::ADMIN}'")
  end

  def can_monitor(user)
    has_privilege(user, Permission::MONITOR)
  end
  def can_delegate(user)
    has_privilege(user, Permission::DELEGATE)
  end
  def is_admin(user)
    has_privilege(user, Permission::ADMIN)
  end

  def get_type_label
    "Hardware Pool"
  end

  def get_controller
    return 'dashboard' 
  end
  def has_privilege(user, privilege)
    pool = self
    # prevent infinite loops
    visited_pools = []
    while (not pool.nil? || visited_pools.include?(pool))
      if (pool.permissions.find(:first, 
                           :conditions => "permissions.privilege = '#{privilege}' and permissions.user = '#{user}'"))
        return true
      end
      visited_pools << pool
      pool = pool.superpool
    end
    return false
  end

  def move_contents_and_destroy
    superpool_id = superpool.id
    hosts.each do |host| 
      host.hardware_pool_id=superpool_id
      host.save
    end
    storage_pools.each do |vol| 
      vol.hardware_pool_id=superpool_id
      vol.save
    end
    # what about quotas -- for now they're deleted
    destroy
  end

  def total_storage_volumes
    storage_pools.inject(0) { |sum, pool| sum += pool.storage_volumes.size}
  end
  def storage_volumes
    storage_pools.collect { |pool| pool.storage_volumes}.flatten
  end
end
