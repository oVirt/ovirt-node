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

class Quota < ActiveRecord::Base
  belongs_to :pool


  def total_vmemory_in_mb
    kb_to_mb(total_vmemory)
  end

  def total_vmemory_in_mb=(mem)
    self[:total_vmemory]=(mb_to_kb(mem))
  end

  def total_storage_in_gb
    kb_to_gb(total_storage)
  end

  def total_storage_in_gb=(storage)
    self[:total_storage]=(gb_to_kb(storage))
  end

  def total_resources
    return Quota.get_resource_hash(total_vcpus, total_vmemory, total_vnics, total_vms, total_storage)
  end

  def self.subtract_resource_hash(total,used)
    self.get_resource_hash((total[:cpus] - used[:cpus] if total[:cpus]),
                      (total[:memory] - used[:memory] if total[:memory]),
                      (total[:nics] - used[:nics] if total[:nics]),
                      (total[:vms] - used[:vms] if total[:vms]),
                      (total[:storage] - used[:storage] if total[:storage]))
  end

  def self.get_resource_hash(cpus, memory, nics, vms, storage)
    return { :cpus => cpus,
             :memory => memory,
             :memory_in_mb => kb_to_mb(memory),
             :nics => nics,
             :vms => vms,
             :storage => storage,
             :storage_in_gb => kb_to_gb(storage)}
  end

end

