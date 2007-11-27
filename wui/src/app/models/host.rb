require 'util/ovirt'

class Host < ActiveRecord::Base
  has_many :nics, :dependent => :destroy
  has_many :vms, :dependent => :nullify
  has_and_belongs_to_many :storage_volumes

  def memory_in_gb
    kb_to_gigs(memory)
  end
  def memory_in_gb=(mem)
    self[:memory]=(gigs_to_kb(mem))
  end
end
