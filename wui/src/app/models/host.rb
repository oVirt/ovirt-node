require 'util/ovirt'

class Host < ActiveRecord::Base
  has_many :nics, :dependent => :destroy
  has_many :vms, :dependent => :nullify
  has_and_belongs_to_many :storage_volumes

  def memory_in_mb
    kb_to_mb(memory)
  end
  def memory_in_mb=(mem)
    self[:memory]=(mb_to_kb(mem))
  end
end
