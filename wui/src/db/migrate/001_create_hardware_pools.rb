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

class CreateHardwarePools < ActiveRecord::Migration
  def self.up
    create_table :hardware_pools do |t|
      t.column :name,               :string
      t.column :type,               :string
      t.column :superpool_id,       :integer
    end

    execute "alter table hardware_pools add constraint fk_hr_pool_superpool
             foreign key (superpool_id) references hardware_pools(id)"
    mp = MotorPool.create( :name=>'default')
    pool = OrganizationalPool.create( :name=>'default', :superpool_id => mp.id)
    map = NetworkMap.create( :name=>'network map', :superpool_id => pool.id)
    collection = HostCollection.create( :name=>'host collection', :superpool_id => map.id)
  end

  def self.down
    drop_table :hardware_pools
  end
end
