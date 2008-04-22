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
  acts_as_nested_set

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

  has_one :quota, :dependent => :destroy

  def create_with_parent(parent)
    transaction do
      save
      move_to_child_of(parent)
    end
  end


  def self.list_for_user(user)
    find(:all, :include => "permissions", 
         :conditions => "permissions.user='#{user}' and permissions.privilege='#{Permission::ADMIN}'")
  end

  def sub_hardware_pools
    children.select {|pool| pool[:type] == "HardwarePool"}
  end
  def sub_vm_resource_pools
    children.select {|pool| pool[:type] == "VmResourcePool"}
  end
  def self_and_like_siblings
    self_and_siblings.select {|pool| pool[:type] == self.class.name}
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
    self_and_ancestors.reverse_each do |the_pool|
      val = yield the_pool
      return val if val
    end
    return nil
  end

end
