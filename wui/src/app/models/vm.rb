class Vm < ActiveRecord::Base
  belongs_to :user
  belongs_to :host
  has_and_belongs_to_many :storage_volumes
end
