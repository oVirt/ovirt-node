class CreateStorageVolumes < ActiveRecord::Migration
  def self.up
    create_table :storage_volumes do |t|
      t.column :ip_addr,      :string
      t.column :port,         :integer
      t.column :target,       :string
      t.column :lun,          :string
      t.column :storage_type, :string
      t.column :size,         :integer
    end

    create_table :hosts_storage_volumes, :id => false do |t|
      t.column :host_id,           :integer, :null => false
      t.column :storage_volume_id, :integer, :null => false
    end

    execute "alter table hosts_storage_volumes add constraint fk_hosts_stor_vol_host_id
             foreign key (host_id) references hosts(id)"
    execute "alter table hosts_storage_volumes add constraint fk_hosts_stor_vol_stor_vol_id
             foreign key (storage_volume_id) references storage_volumes(id)"

  end

  def self.down
    drop_table :hosts_storage_volumes
    drop_table :storage_volumes
  end
end
