class CreateHardwarePools < ActiveRecord::Migration
  def self.up
    create_table :hardware_pools do |t|
      t.column :name,               :string
      t.column :type,               :string
      t.column :superpool_id,       :integer
    end

    execute "alter table hardware_pools add constraint fk_hr_pool_superpool
             foreign key (superpool_id) references hardware_pools(id)"
    mp = MotorPool.create( :name=>'default')
    pool = OrganizationalPool.create( :name=>'default', :superpool_id => mp.id)
    map = NetworkMap.create( :name=>'default', :superpool_id => pool.id)
    collection = HostCollection.create( :name=>'default', :superpool_id => map.id)
  end

  def self.down
    drop_table :hardware_pools
  end
end
