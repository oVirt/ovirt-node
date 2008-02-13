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
    create_table :storage_volumes do |t|
      t.column :ip_addr,                    :string
      t.column :port,                       :integer
      t.column :target,                     :string
      t.column :lun,                        :string
      t.column :storage_type,               :string
      t.column :size,                       :integer
      t.column :hardware_pool_id,           :integer, :null => false
    end

    execute "alter table storage_volumes add constraint fk_storage_volume_hw_pools
             foreign key (hardware_pool_id) references hardware_pools(id)"

  end

  def self.down
    drop_table :storage_volumes
  end
end
