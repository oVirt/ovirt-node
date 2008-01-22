class Permission < ActiveRecord::Base
  # should belong_to _either_ a Hardware Pool _or_ a Quota -- not both
  belongs_to :hardware_pool
  belongs_to :quota

  MONITOR = "monitor"
  ADMIN = "admin"
  DELEGATE = "delegate"
  PRIVILEGES = [["Monitor", MONITOR], 
                ["Admin", ADMIN],
                ["Delegate", DELEGATE]]
end
