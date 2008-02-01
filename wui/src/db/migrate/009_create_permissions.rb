class CreatePermissions < ActiveRecord::Migration
  def self.up
    create_table :permissions do |t|
      t.column :privilege,                  :string
      t.column :user,                       :string
      t.column :hardware_pool_id,           :integer
      t.column :vm_library_id,              :integer
    end
    execute "alter table permissions add constraint fk_permissions_hw_pools
             foreign key (hardware_pool_id) references hardware_pools(id)"
    execute "alter table permissions add constraint fk_permissions_vm_libraries
             foreign key (vm_library_id) references vm_libraries(id)"
  end


  def self.down
    drop_table :permissions
  end
end
