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

class CreateTasks < ActiveRecord::Migration
  def self.up
    create_table :tasks do |t|
      t.column :user,              :string
      t.column :vm_id,             :integer, :null => false
      t.column :action,            :string
      t.column :state,             :string
      t.column :args,              :string
      t.column :created_at,        :timestamp
      t.column :time_started,      :timestamp
      t.column :time_ended,        :timestamp
      t.column :message,           :text
    end
    execute "alter table tasks add constraint fk_tasks_vms
             foreign key (vm_id) references vms(id)"
  end

  def self.down
    drop_table :tasks
  end
end
