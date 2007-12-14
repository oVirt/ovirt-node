require 'util/ovirt'

class StorageVolume < ActiveRecord::Base
  belongs_to              :hardware_resource_group
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
    condition =  "vms.id is null"
    condition += " or vms.id=#{include_vm.id}" if (include_vm and include_vm.id)
    StorageVolume.find(:all, :include => [:vms], :conditions => condition)
  end
end
