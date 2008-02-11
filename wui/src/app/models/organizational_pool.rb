class OrganizationalPool < HardwarePool

  has_many :network_maps, :class_name => "NetworkMap", :foreign_key => "superpool_id", :dependent => :nullify

  def host_collections
    network_maps.collect{ |map| map.host_collections }.flatten
  end

  def get_type_label
    "Organizational Pool"
  end
end
