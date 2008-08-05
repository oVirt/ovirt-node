class CreateActsAsXapian < ActiveRecord::Migration
  def self.up
    create_table :acts_as_xapian_jobs do |t|
      t.column :model, :string, :null => false
      t.column :model_id, :integer, :null => false
      t.column :action, :string, :null => false
    end
    add_index :acts_as_xapian_jobs, [:model, :model_id], :unique => true

    begin
      root_pool = HardwarePool.get_default_pool
      new_root = HardwarePool.create( :name=>'default') unless root_pool
    rescue
      puts "Could not create default pool..."
    end
  end
  def self.down
    drop_table :acts_as_xapian_jobs
  end

end

