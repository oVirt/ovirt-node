class StorageVolume < ActiveRecord::Base
  has_and_belongs_to_many :hosts
  has_and_belongs_to_many :vms
end
