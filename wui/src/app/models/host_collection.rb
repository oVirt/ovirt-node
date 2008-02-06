class HostCollection < HardwarePool
  has_many :vm_libraries, :dependent => :destroy, :order => "id ASC"
  has_one :quota, :dependent => :destroy

  def get_type_label
    "Host Collection"
  end

end
