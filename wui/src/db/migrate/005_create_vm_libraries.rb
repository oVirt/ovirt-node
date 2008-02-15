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

class CreateVmLibraries < ActiveRecord::Migration
  def self.up
    create_table :vm_libraries do |t|
      t.column :name,                       :string
      t.column :host_collection_id,         :integer, :null => false
    end
    execute "alter table vm_libraries add constraint fk_libraries_hw_pools
             foreign key (host_collection_id) references hardware_pools(id)"
  end

  def self.down
    drop_table :vm_libraries
  end
end
