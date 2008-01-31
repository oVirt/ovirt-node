class CreateStorageVolumes < ActiveRecord::Migration
  def self.up
    create_table :storage_volumes do |t|
      t.column :ip_addr,                    :string
      t.column :port,                       :integer
      t.column :target,                     :string
      t.column :lun,                        :string
      t.column :storage_type,               :string
      t.column :size,                       :integer
      t.column :hardware_pool_id,           :integer, :null => false
    end

    execute "alter table storage_volumes add constraint fk_storage_volume_hw_pools
             foreign key (hardware_pool_id) references hardware_pools(id)"

  end

  def self.down
    drop_table :storage_volumes
  end
end
