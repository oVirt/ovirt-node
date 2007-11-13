class CreateUserQuotas < ActiveRecord::Migration
  def self.up
    create_table :user_quotas do |t|
      t.column :user_id,         :integer, :null => false
      t.column :total_vcpus,     :integer
      t.column :total_vmemory,   :integer
      t.column :total_vnics,     :integer
      t.column :total_storage,   :integer
    end
    execute "alter table user_quotas add constraint fk_user_quotas_users
             foreign key (user_id) references users(id)"
  end

  def self.down
    drop_table :user_quotas
  end
end
