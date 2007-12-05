require 'util/ovirt'

class UserQuota < ActiveRecord::Base
  belongs_to :user
  validates_presence_of :total_vcpus, :total_memory, :total_vnics, :total_storage

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

  def allocated_resources(exclude_vm = nil)
    cpus = 0
    memory = 0
    nics = 0
    storage = 0
    self.user.vms.each do |vm|
      unless (exclude_vm and exclude_vm.id == vm.id)
        cpus += vm.num_vcpus_allocated
        memory += vm.memory_allocated
        # a vNIC per VM for now
        nics += 1
        vm.storage_volumes.each do |volume|
          storage += volume.size
        end
      end
    end
    return get_resource_hash(cpus, memory, nics, storage)
  end

  def total_resources
    return get_resource_hash(total_vcpus, total_vmemory, total_vnics, total_storage)
  end

  def full_resources(exclude_vm = nil)
    total = total_resources
    allocated = allocated_resources(exclude_vm)
    available = get_resource_hash(total[:cpus] - allocated[:cpus],
                                  total[:memory] - allocated[:memory],
                                  total[:nics] - allocated[:nics],
                                  total[:storage] - allocated[:storage])
    labels = [["CPUs", :cpus, ""], 
              ["Memory", :memory_in_mb, "(mb)"], 
              ["NICs", :nics, ""], 
              ["Disk", :storage_in_gb, "(gb)"]]
    return {:total => total, :allocated => allocated, :available => available,
            :labels => labels}
  end

  def get_resource_hash(cpus, memory, nics, storage)
    return { :cpus => cpus,
             :memory => memory,
             :memory_in_mb => kb_to_mb(memory),
             :nics => nics,
             :storage => storage,
             :storage_in_gb => kb_to_gb(storage)}
  end

  def available_resources(exclude_vm = nil)
    return full_resources(exclude_vm)[:available]
  end

  def available_resources_for_vm(vm = nil)
    resources = full_resources(vm)[:available]
    host_mem_limit = Host.find(:first, :order => "memory DESC").memory
    host_cpu_limit = Host.find(:first, :order => "num_cpus DESC").num_cpus
    resources[:memory] = host_mem_limit if host_mem_limit < resources[:memory]
    resources[:cpus] = host_cpu_limit if host_cpu_limit < resources[:cpus]
    # update mb/gb values
    return get_resource_hash(resources[:cpus], resources[:memory], 
                             resources[:nics], resources[:storage])
  end
end
