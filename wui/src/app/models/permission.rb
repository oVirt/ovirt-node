class Permission < ActiveRecord::Base
  # should belong_to _either_ a Hardware Pool _or_ a VM Library -- not both
  belongs_to :hardware_pool
  belongs_to :vm_library

  MONITOR = "monitor"
  ADMIN = "admin"
  DELEGATE = "delegate"
  PRIVILEGES = [["Monitor", MONITOR], 
                ["Admin", ADMIN],
                ["Delegate", DELEGATE]]
end
