class MotorPool < HardwarePool

  has_many :organizational_pools, :class_name => "OrganizationalPool", :foreign_key => "superpool_id"

  def get_type_label
    "Motor Pool"
  end
end
