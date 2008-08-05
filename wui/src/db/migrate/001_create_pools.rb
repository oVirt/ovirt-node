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

class CreatePools < ActiveRecord::Migration
  def self.up
    create_table :pools do |t|
      t.string :name
      t.string :type
      t.integer :parent_id
      t.integer :lft
      t.integer :rgt
      t.integer :lock_version, :default => 0
      t.timestamps
    end

    execute "alter table pools add constraint fk_pool_parent
             foreign key (parent_id) references pools(id)"
  end

  def self.down
    drop_table :pools
  end
end
