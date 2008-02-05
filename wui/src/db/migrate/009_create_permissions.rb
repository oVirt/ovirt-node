class CreatePermissions < ActiveRecord::Migration
  def self.up
    create_table :permissions do |t|
      t.column :privilege,                  :string
      t.column :user,                       :string
      t.column :hardware_pool_id,           :integer
      t.column :vm_library_id,              :integer
    end
  end


  def self.down
    drop_table :permissions
  end
end
