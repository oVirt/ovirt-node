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

class AddPoolsToTasks < ActiveRecord::Migration
  def self.up
    add_column :tasks, :vm_resource_pool_id, :integer
    add_column :tasks, :hardware_pool_id, :integer
    execute "alter table tasks add constraint fk_tasks_vm_pools
             foreign key (vm_resource_pool_id) references pools(id)"
    execute "alter table tasks add constraint fk_tasks_hw_pools
             foreign key (hardware_pool_id) references pools(id)"
    Task.transaction do
      VmTask.find(:all).each do |task|
        vm = task.vm
        if vm
          task.vm_resource_pool = vm.vm_resource_pool
          task.hardware_pool = vm.get_hardware_pool
          task.save!
        end
      end
      StorageTask.find(:all).each  do |task|
        pool = task.storage_pool
        if pool
          task.hardware_pool = pool.hardware_pool
          task.save!
        end
      end
      HostTask.find(:all).each do |task|
        host = task.host
        if host
          task.hardware_pool = host.hardware_pool
          task.save!
        end
      end
    end
  end

  def self.down
    remove_column :tasks, :vm_resource_pool_id
    remove_column :tasks, :hardware_pool_id
  end
end
