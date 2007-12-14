class Permission < ActiveRecord::Base
  # should belong_to _either_ a Hardware Resource Group _or_ a Quota -- not both
  belongs_to :hardware_resource_group
  belongs_to :quota

  MONITOR = "monitor"
  ADMIN = "admin"
  DELEGATE = "delegate"
  PRIVILEGES = [MONITOR, ADMIN, DELEGATE]
end
