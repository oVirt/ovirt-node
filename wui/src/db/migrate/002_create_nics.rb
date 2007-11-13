class CreateNics < ActiveRecord::Migration
  def self.up
    create_table :nics do |t|
      t.column :mac,         :string
      t.column :ip_addr,     :string
      t.column :usage_type,  :string
      t.column :bandwidth,   :integer
      t.column :host_id,     :integer, :null => false
    end

    execute "alter table nics add constraint fk_nic_hosts
             foreign key (host_id) references hosts(id)"

  end

  def self.down
    drop_table :nics
  end
end
