class CreatePermissions < ActiveRecord::Migration
  def self.up
    create_table :permissions do |t|
      t.column :privilege,                  :string
      t.column :user,                       :string
      t.column :hardware_resource_group_id, :integer
      t.column :quota_id,                   :integer
    end
    execute "alter table permissions add constraint fk_permissions_hw_groups
             foreign key (hardware_resource_group_id) references hardware_resource_groups(id)"
    execute "alter table permissions add constraint fk_permissions_quotas
             foreign key (quota_id) references quotas(id)"
  end


  def self.down
    drop_table :permissions
  end
end
