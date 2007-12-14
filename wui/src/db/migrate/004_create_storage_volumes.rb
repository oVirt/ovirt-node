class CreateStorageVolumes < ActiveRecord::Migration
  def self.up
    create_table :storage_volumes do |t|
      t.column :ip_addr,                    :string
      t.column :port,                       :integer
      t.column :target,                     :string
      t.column :lun,                        :string
      t.column :storage_type,               :string
      t.column :size,                       :integer
      t.column :hardware_resource_group_id, :integer
    end

    execute "alter table storage_volumes add constraint fk_storage_volume_hw_groups
             foreign key (hardware_resource_group_id) references hardware_resource_groups(id)"

  end

  def self.down
    drop_table :hosts_storage_volumes
    drop_table :storage_volumes
  end
end
