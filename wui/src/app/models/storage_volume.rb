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

require 'util/ovirt'

class StorageVolume < ActiveRecord::Base
  belongs_to              :storage_pool
  has_and_belongs_to_many :vms

  def self.factory(type, params = nil)
    case type
    when "iSCSI"
      return IscsiStorageVolume.new(params)
    when "NFS"
      return NfsStorageVolume.new(params)
    else
      return nil
    end
  end

  def get_type_label
    StoragePool::STORAGE_TYPES.invert[self.class.name.gsub("StorageVolume", "")]
  end

  def display_name
    "#{get_type_label}: #{storage_pool.ip_addr}:#{label_components}"
  end

  def size_in_gb
    kb_to_gb(size)
  end

  def size_in_gb=(new_size)
    self[:size]=(gb_to_kb(new_size))
  end

  def self.find_for_vm(include_vm, vm_pool)
    if vm_pool
      condition =  "(vms.id is null and storage_pools.hardware_pool_id=#{vm_pool.get_hardware_pool.id})"
      condition += " or vms.id=#{include_vm.id}" if (include_vm and include_vm.id)
      self.find(:all, :include => [:vms, :storage_pool], :conditions => condition)
    else
      return []
    end
  end
end
