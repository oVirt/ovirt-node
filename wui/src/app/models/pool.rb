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

  # used to allow parent traversal before obj is saved to the db 
  # (needed for view code 'create' form)
  attr_accessor :tmp_parent

  # overloading this method such that we can use permissions.admins to get all the admins for an object
  has_many :permissions, :dependent => :destroy, :order => "id ASC" do
    def super_admins
      find_all_by_user_role(Permission::ROLE_SUPER_ADMIN)
    end
    def admins
      find_all_by_user_role(Permission::ROLE_ADMIN)
    end
    def users
      find_all_by_user_role(Permission::ROLE_USER)
    end
    def monitors
      find_all_by_user_role(Permission::ROLE_MONITOR)
    end
  end

  has_one :quota, :dependent => :destroy

  def create_with_parent(parent)
    transaction do
      save
      move_to_child_of(parent)
    end
  end

  # this method lists pools with direct permission grants, but does not 
  # include implied permissions (i.e. subtrees)
  def self.list_for_user(user, privilege)
    pools = find(:all, :include => "permissions", 
                 :conditions => "permissions.uid='#{user}' and 
                       permissions.user_role in 
                       ('#{Permission.roles_for_privilege(privilege).join("', '")}')")
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

  def can_view(user)
    has_privilege(user, Permission::PRIV_VIEW)
  end
  def can_control_vms(user)
    has_privilege(user, Permission::PRIV_VM_CONTROL)
  end
  def can_modify(user)
    has_privilege(user, Permission::PRIV_MODIFY)
  end
  def can_view_perms(user)
    has_privilege(user, Permission::PRIV_PERM_VIEW)
  end
  def can_set_perms(user)
    has_privilege(user, Permission::PRIV_PERM_SET)
  end

  def has_privilege(user, privilege)
    traverse_parents do |pool|
      pool.permissions.find(:first, 
                            :conditions => "permissions.uid='#{user}' and 
                         permissions.user_role in 
                         ('#{Permission.roles_for_privilege(privilege).join("', '")}')")
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

  #needed by tree widget for display
  def hasChildren
    return (rgt - lft) != 1
  end

  def self.nav_json(pools, open_list)
    pool_hash(pools, open_list).to_json
  end
  def self.pool_hash(pools, open_list)
    pools.collect do |pool|
      hash = {}
      hash[:id] = pool.id
      hash[:type] = pool[:type]
      hash[:text] = pool.name
      hash[:name] = pool.name
      hash[:hasChildren] = pool.hasChildren
      found = false
      open_list.each do |open_pool|
        if pool.id == open_pool.id
          new_open_list = open_list[(open_list.index(open_pool)+1)..-1]          
          unless new_open_list.empty?
            hash[:children] = pool_hash(pool.children, new_open_list)
            hash[:expanded] = true
            hash.delete(:hasChildren)
          end
          break
        end
      end
      hash
    end
  end
    

  protected
  def traverse_parents
    if id
      ancestor_array = self_and_ancestors
    elsif tmp_parent
      ancestor_array = tmp_parent.self_and_ancestors
    else
      ancestor_array = []
    end
    ancestor_array.reverse_each do |the_pool|
      val = yield the_pool
      return val if val
    end
    return nil
  end


end
