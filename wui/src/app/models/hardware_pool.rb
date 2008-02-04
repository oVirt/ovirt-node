class HardwarePool < ActiveRecord::Base
  has_many :permissions, :dependent => :destroy, :order => "id ASC"

  has_many :hosts, :dependent => :nullify, :order => "id ASC"
  has_many :storage_volumes, :dependent => :nullify, :order => "id ASC"
  belongs_to :superpool, :class_name => "HardwarePool", :foreign_key => "superpool_id"
  has_many :subpools, :class_name => "HardwarePool", :foreign_key => "superpool_id", :dependent => :nullify, :order => "id ASC"
  has_many :vm_libraries, :dependent => :destroy, :order => "id ASC"
  has_one :quota, :dependent => :destroy


  def self.list_for_user(user)
    find(:all, :include => "permissions", 
         :conditions => "permissions.user='#{user}' and permissions.privilege='#{Permission::ADMIN}'")
  end

  def self.get_default_pool
    find(:first, :include => "permissions", :order => "hardware_pools.id ASC", 
         :conditions => "superpool_id is null")
  end

  def can_monitor(user)
    has_privilege(user, Permission::MONITOR)
  end
  def can_delegate(user)
    has_privilege(user, Permission::DELEGATE)
  end
  def is_admin(user)
    has_privilege(user, Permission::ADMIN)
  end

  def is_organizational
    val = read_attribute(:is_organizational)
    return val == 1 ? val : nil
  end
  def is_network_map
    val = read_attribute(:is_network_map)
    return val == 1 ? val : nil
  end
  def is_host_collection
    val = read_attribute(:is_host_collection)
    return val == 1 ? val : nil
  end

  def get_type_label
    labels = []
    labels << "Hardware Pool" if is_organizational
    labels << "Network Map" if is_network_map
    labels << "Host Collection" if is_host_collection
    labels.join(", ")
  end

  # for a given pool type and value (set vs. unset), is the operation allowable
  def is_type_update_ok?(attribute, val)
    if (attribute == "is_organizational")
      val.nil? ? unset_org_pool_ok? : org_pool_ok?
    elsif (attribute == "is_network_map")
      val.nil? ? unset_network_map_ok? : network_map_ok?
    elsif (attribute == "is_host_collection")
      val.nil? ? unset_host_collection_ok? : host_collection_ok?
    else
      false
    end
  end
  # a pool can be an OP if:
  # 1) it has no parent or its parent is OP
  # 2) if it's an HC it's also an NM
  # 3) If it's not an NM, Children are either OP or NM
  # 4) it's not already an OP
  def org_pool_ok?
    (not is_organizational) and
    (superpool.nil? or superpool.is_organizational) and
      (is_network_map or 
       ((not is_host_collection) and
        subpools.select { |x| not(x.is_organizational or x.is_network_map)}.empty?))
  end
  # a pool can be an NM if:
  # 1) its parent is not nil (i.e. it's not the motor pool)
  # 2) its parent (or self) is an OP 
  # 3) children are all HC but not NM
  # 4) it's not already an NM
  def network_map_ok?
    (not is_network_map) and
    (not superpool.nil?) and 
      (superpool.is_organizational or is_organizational) and
      subpools.select { |x| ((not x.is_host_collection) or x.is_network_map)}.empty?
  end
  # a pool can be an HC if:
  # 1) its parent (or self) is an NM or parent is an HC 
  # 2) if it's an OP it's also an NM
  # 2) children are all HC but not NM
  # 4) it's not already an HC
  def host_collection_ok?
    (not is_host_collection) and
    (not superpool.nil?) and 
      (superpool.is_network_map or superpool.is_host_collection or is_network_map) and
      (is_network_map or (not is_organizational)) and
      subpools.select { |x| ((not x.is_host_collection) or x.is_network_map)}.empty?
  end

  # OP must remain an OP unless it's already a NM and has an OP parent
  def unset_org_pool_ok?
    (not superpool.nil?) and is_network_map and is_organizational
  end
  # NM must remain an NM unless it's also an OP and has no children
  def unset_network_map_ok?
    is_organizational and subpools.empty? and is_network_map and (not is_host_collection)
  end
  # HC must remain an HC unless it's also an NM and has no VM Libraries
  def unset_host_collection_ok?
    is_network_map and vm_libraries.empty? and is_host_collection
  end

  # a subpool can be an OP if:
  # 1) parent (this pool) is OP and not NM
  def sub_org_pool_ok?
    is_organizational and (not is_network_map)
  end
  # a subpool can be an NM if:
  # 1) parent (this pool) is OP and not NM and this pool has a parent 
  #    (to exclude motor pool)
  def sub_network_map_ok?
    is_organizational and (not is_network_map) and (not superpool.nil?)
  end
  # a subpool can be an HC if:
  # 1) parent (this pool) is NM or HC
  def sub_host_collection_ok?
    (is_host_collection or is_network_map)
  end

  def has_privilege(user, privilege)
    pool = self
    # prevent infinite loops
    visited_pools = []
    while (not pool.nil? || visited_pools.include?(pool))
      if (pool.permissions.find(:first, 
                           :conditions => "permissions.privilege = '#{privilege}' and permissions.user = '#{user}'"))
        return true
      end
      visited_pools << pool
      pool = pool.superpool
    end
    return false
  end

end
