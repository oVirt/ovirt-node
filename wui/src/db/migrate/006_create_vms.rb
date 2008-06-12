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

class CreateVms < ActiveRecord::Migration
  def self.up
    create_table :vms do |t|
      t.string  :uuid
      t.string  :description
      t.integer :num_vcpus_allocated
      t.integer :num_vcpus_used
      t.integer :memory_allocated
      t.integer :memory_used
      t.string  :vnic_mac_addr
      t.string  :state
      t.integer :host_id
      t.integer :vm_resource_pool_id
      t.integer :needs_restart
      t.string  :boot_device,    :null => false
      t.integer :vnc_port
      t.integer :lock_version,   :default => 0
    end
    execute "alter table vms add constraint fk_vms_hosts
             foreign key (host_id) references hosts(id)"
    execute "alter table vms add constraint fk_vms_vm_pools
             foreign key (vm_resource_pool_id) references pools(id)"

    create_table :storage_volumes_vms, :id => false do |t|
      t.integer :vm_id,             :null => false
      t.integer :storage_volume_id, :null => false
    end
    execute "alter table storage_volumes_vms add constraint
             fk_stor_vol_vms_vm_id
             foreign key (vm_id) references vms(id)"
    execute "alter table storage_volumes_vms add constraint
             fk_stor_vol_vms_stor_vol_id
             foreign key (storage_volume_id) references storage_volumes(id)"
  end

  def self.down
    drop_table :storage_volumes_vms
    drop_table :vms
  end
end
