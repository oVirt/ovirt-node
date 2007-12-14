require 'util/ovirt'

class Host < ActiveRecord::Base
  belongs_to :hardware_resource_group
  has_many :nics, :dependent => :destroy
  has_many :vms, :dependent => :nullify

  def memory_in_mb
    kb_to_mb(memory)
  end
  def memory_in_mb=(mem)
    self[:memory]=(mb_to_kb(mem))
  end
end
