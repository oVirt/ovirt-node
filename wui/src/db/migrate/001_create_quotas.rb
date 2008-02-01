class CreateQuotas < ActiveRecord::Migration
  def self.up
    create_table :quotas do |t|
      t.column :total_vcpus,                :integer
      t.column :total_vmemory,              :integer
      t.column :total_vnics,                :integer
      t.column :total_storage,              :integer
      t.column :total_vms,                  :integer
    end
  end

  def self.down
    drop_table :quotas
  end
end
