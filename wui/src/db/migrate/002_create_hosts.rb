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

class CreateHosts < ActiveRecord::Migration
  def self.up
    create_table :hosts do |t|
      t.string  :uuid
      t.string  :hypervisor_type
      t.string  :hostname
      t.integer :num_cpus
      t.integer :cpu_speed
      t.string  :arch
      t.integer :memory
      t.integer :is_disabled
      t.integer :hardware_pool_id, :null => false
      t.integer :lock_version,     :default => 0
      t.string  :state
      t.float   :load_average
      t.timestamps
    end

    execute "alter table hosts add constraint fk_host_pools
             foreign key (hardware_pool_id) references pools(id)"
  end

  def self.down
    drop_table :hosts
  end
end
