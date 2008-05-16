class RenameUserToUidInPermissions < ActiveRecord::Migration
  def self.up
    rename_column :permissions, :user, :uid
  end

  def self.down
    rename_column :permissions, :uid, :user
  end
end
