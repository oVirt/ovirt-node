class NetworkMap < HardwarePool

  belongs_to :organizational_pool, :class_name => "OrganizationalPool", :foreign_key => "superpool_id"
  has_many :host_collections, :class_name => "HostCollection", :foreign_key => "superpool_id", :dependent => :nullify

  def get_type_label
    "Network Map"
  end

end
