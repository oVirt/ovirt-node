class Host < ActiveRecord::Base
  has_many :nics, :dependent => :destroy
  has_many :vms, :dependent => :nullify
  has_and_belongs_to_many :storage_volumes
end
