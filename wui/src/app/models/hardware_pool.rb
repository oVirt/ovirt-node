class HardwarePool < ActiveRecord::Base
  has_many :permissions, :dependent => :destroy, :order => "id ASC"

  has_many :hosts, :dependent => :nullify, :order => "id ASC"
  has_many :storage_volumes, :dependent => :nullify, :order => "id ASC"
  belongs_to :superpool, :class_name => "HardwarePool", :foreign_key => "superpool_id"
  has_many :subpools, :class_name => "HardwarePool", :foreign_key => "superpool_id", :dependent => :nullify, :order => "id ASC"


  def self.factory(type, params = nil)
    case type
      when MotorPool.name
        return MotorPool.new(params)
      when OrganizationalPool.name
        return OrganizationalPool.new(params)
      when NetworkMap.name
        return NetworkMap.new(params)
      when HostCollection.name
        return HostCollection.new(params)
      else
        return nil
    end
  end

  def self.list_for_user(user)
    find(:all, :include => "permissions", 
         :conditions => "permissions.user='#{user}' and permissions.privilege='#{Permission::ADMIN}'")
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

  def get_type_label
    "Hardware Pool"
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
