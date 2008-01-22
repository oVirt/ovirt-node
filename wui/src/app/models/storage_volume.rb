require 'util/ovirt'

class StorageVolume < ActiveRecord::Base
  belongs_to              :hardware_pool
  has_and_belongs_to_many :vms

  def display_name
    "#{ip_addr}:#{target}:#{lun}"
  end

  def size_in_gb
    kb_to_gb(size)
  end

  def size_in_gb=(new_size)
    self[:size]=(gb_to_kb(new_size))
  end

  def self.find_for_vm(include_vm = nil)
    if include_vm 
      condition =  "(vms.id is null and hardware_pool_id=#{include_vm.quota.hardware_pool_id})"
      condition += " or vms.id=#{include_vm.id}" if (include_vm.id)
      self.find(:all, :include => [:vms], :conditions => condition)
    else
      return []
    end
  end
end
