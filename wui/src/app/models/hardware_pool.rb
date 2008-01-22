class HardwarePool < ActiveRecord::Base
  has_many :permissions, :dependent => :destroy, :order => "id ASC"

  has_many :hosts, :dependent => :nullify, :order => "id ASC"
  has_many :storage_volumes, :dependent => :nullify, :order => "id ASC"
  belongs_to :superpool, :class_name => "HardwarePool", :foreign_key => "superpool_id"
  # a Hardware Pool should, at any one time, have only
  # subpools _or_ quotas
  has_many :subpools, :class_name => "HardwarePool", :foreign_key => "superpool_id", :dependent => :nullify, :order => "id ASC"
  has_many :quotas, :dependent => :destroy, :order => "id ASC"


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
