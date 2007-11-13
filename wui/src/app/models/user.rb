class User < ActiveRecord::Base
  has_one  :user_quota, :dependent => :nullify
  has_many :vms, :dependent => :nullify
end
