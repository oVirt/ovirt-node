class StorageVolume < ActiveRecord::Base
  has_and_belongs_to_many :hosts
  has_and_belongs_to_many :vms

  def display_name
    "#{ip_addr}:#{target}:#{lun}"
  end

  def self.find_for_vm(include_vm = nil)
    condition =  "vms.id is null"
    condition += " or vms.id=#{include_vm.id}" if include_vm
    StorageVolume.find(:all, :include => [:vms], :conditions => condition)
  end
end
