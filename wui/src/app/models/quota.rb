require 'util/ovirt'

class Quota < ActiveRecord::Base
  # should belong_to _either_ a Hardware Pool _or_ a VM Library -- not both
  belongs_to :hardware_pool
  belongs_to :vm_library

  validates_presence_of :total_vcpus, :total_vmemory, :total_vnics, :total_storage

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

