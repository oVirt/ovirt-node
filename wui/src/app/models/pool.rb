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

class Pool < ActiveRecord::Base
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

  belongs_to :superpool, :class_name => "Pool", :foreign_key => "superpool_id"
  has_many :subpools, :class_name => "Pool", :foreign_key => "superpool_id", :dependent => :destroy, :order => "id ASC"
  has_one :quota, :dependent => :destroy

  def self.list_for_user(user)
    find(:all, :include => "permissions", 
         :conditions => "permissions.user='#{user}' and permissions.privilege='#{Permission::ADMIN}'")
  end

  def sub_hardware_pools
    subpools.select {|pool| pool[:type] == "HardwarePool"}
  end
  def sub_vm_resource_pools
    subpools.select {|pool| pool[:type] == "VmResourcePool"}
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

  def has_privilege(user, privilege)
    traverse_parents do |pool|
      pool.permissions.find(:first, 
                            :conditions => "permissions.privilege = '#{privilege}' and permissions.user = '#{user}'")
    end
  end

  def total_resources
    the_quota = traverse_parents { |pool| pool.quota }
    if the_quota.nil?
      Quota.get_resource_hash(nil, nil, nil, nil, nil)
    else
      the_quota.total_resources
    end
  end

  RESOURCE_LABELS = [["CPUs", :cpus, ""], 
                     ["Memory", :memory_in_mb, "(mb)"], 
                     ["NICs", :nics, ""], 
                     ["VMs", :vms, ""], 
                     ["Disk", :storage_in_gb, "(gb)"]]

  protected
  def traverse_parents
    the_pool = self
    # prevent infinite loops
    visited_pools = []
    while (not (the_pool.nil? || visited_pools.include?(the_pool)))
      val = yield the_pool
      return val if val
      visited_pools << the_pool
      the_pool = the_pool.superpool
    end
    return nil
  end

end
