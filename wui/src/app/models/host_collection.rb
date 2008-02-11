class HostCollection < HardwarePool
  has_many :vm_libraries, :dependent => :destroy, :order => "id ASC"
  has_one :quota, :dependent => :destroy

  belongs_to :network_map, :class_name => "NetworkMap", :foreign_key => "superpool_id"

  def get_type_label
    "Host Collection"
  end

end
