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

class CreateStorageVolumes < ActiveRecord::Migration
  def self.up
    create_table :storage_pools do |t|
      t.string :ip_addr
      t.string :type
      t.integer :hardware_pool_id, :null => false
      t.integer :lock_version,     :default => 0

      # for IscsiStoragePool
      t.integer :port
      t.string :target

      # for NfsStoragePool
      t.string :export_path
    end

    create_table :storage_volumes do |t|
      t.string :path
      t.integer :size
      t.integer :storage_pool_id,  :null => false
      t.string :type
      t.integer :lock_version,     :default => 0

      # for IscsiStorageVolume
      t.string :lun

      # for IscsiStorageVolume
      t.string :filename
    end

    execute "alter table storage_pools add constraint fk_storage_pool_pools
             foreign key (hardware_pool_id) references pools(id)"
    execute "alter table storage_volumes add constraint fk_storage_volume_st_pools
             foreign key (storage_pool_id) references storage_pools(id)"

  end

  def self.down
    drop_table :storage_volumes
    drop_table :storage_pools
  end
end
