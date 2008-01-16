class HardwareResourceGroup < ActiveRecord::Base
  has_many :permissions, :dependent => :destroy, :order => "id ASC"

  has_many :hosts, :dependent => :nullify, :order => "id ASC"
  has_many :storage_volumes, :dependent => :nullify, :order => "id ASC"
  belongs_to :supergroup, :class_name => "HardwareResourceGroup", :foreign_key => "supergroup_id"
  # a Hardware Resource Group should, at any one time, have only
  # subgroups _or_ quotas
  has_many :subgroups, :class_name => "HardwareResourceGroup", :foreign_key => "supergroup_id", :dependent => :nullify, :order => "id ASC"
  has_many :quotas, :dependent => :destroy, :order => "id ASC"


  def self.list_for_user(user)
    find(:all, :include => "permissions", 
         :conditions => "permissions.user='#{user}' and permissions.privilege='#{Permission::ADMIN}'")
  end

  def self.get_default_group
    find(:first, :include => "permissions", :order => "hardware_resource_groups.id ASC", 
         :conditions => "supergroup_id is null")
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
    group = self
    # prevent infinite loops
    visited_groups = []
    while (not group.nil? || visited_groups.include?(group))
      if (group.permissions.find(:first, 
                           :conditions => "permissions.privilege = '#{privilege}' and permissions.user = '#{user}'"))
        return true
      end
      visited_groups << group
      group = group.supergroup
    end
    return false
  end

end
