class CreateQuotas < ActiveRecord::Migration
  def self.up
    create_table :quotas do |t|
      t.column :total_vcpus,                :integer
      t.column :total_vmemory,              :integer
      t.column :total_vnics,                :integer
      t.column :total_storage,              :integer
      t.column :total_vms,                  :integer
      t.column :host_collection_id,         :integer
      t.column :vm_library_id,              :integer
    end

    execute "alter table quotas add constraint fk_quotas_hw_pools
             foreign key (host_collection_id) references hardware_pools(id)"
    execute "alter table quotas add constraint fk_quotas_vm_libraries
             foreign key (vm_library_id) references vm_libraries(id)"
  end

  def self.down
    drop_table :quotas
  end
end
