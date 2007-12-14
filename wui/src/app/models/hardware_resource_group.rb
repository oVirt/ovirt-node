class HardwareResourceGroup < ActiveRecord::Base
  # needs to be added to belongs_to obj first
  #has_many :user_permissions, :dependent => :destroy, :order => "id ASC"

  has_many :hosts, :dependent => :nullify, :order => "id ASC"
  has_many :storage_volumes, :dependent => :nullify, :order => "id ASC"
  belongs_to :supergroup, :class_name => "HardwareResourceGroup", :foreign_key => "supergroup_id"
  # a Hardware Resource Group should, at any one time, have only
  # subgroups _or_ quotas
  has_many :subgroups, :class_name => "HardwareResourceGroup", :foreign_key => "supergroup_id", :dependent => :nullify, :order => "id ASC"
  has_many :quotas, :dependent => :destroy, :order => "id ASC"
end
