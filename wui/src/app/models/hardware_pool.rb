class HardwarePool < ActiveRecord::Base

  # overloading this method such that we can use permissions.admins to get all the admins for an object
  has_many :permissions, :dependent => :destroy, :order => "id ASC" do
      def admins
          find_all_by_privilege(Permission::ADMIN)
      end
      def monitors
          find_all_by_privilege(Permission::MONITOR)
      end
      def delegates
          find_all_by_privilege(Permission::DELEGATE)
      end
  end

  has_many :hosts, :dependent => :nullify, :order => "id ASC" do
    def total_cpus
      find(:all).inject(0){ |sum, host| sum + host.num_cpus }
    end
  end

  has_many :storage_volumes, :dependent => :nullify, :order => "id ASC" do
    def total_size_in_gb
      find(:all).inject(0){ |sum, sv| sum + sv.size_in_gb }
    end
  end

  belongs_to :superpool, :class_name => "HardwarePool", :foreign_key => "superpool_id"
#  has_many :subpools, :class_name => "HardwarePool", :foreign_key => "superpool_id", :dependent => :nullify, :order => "id ASC"

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
