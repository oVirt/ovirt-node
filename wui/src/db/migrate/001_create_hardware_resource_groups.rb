class CreateHardwareResourceGroups < ActiveRecord::Migration
  def self.up
    create_table :hardware_resource_groups do |t|
      t.column :name,           :string
      t.column :supergroup_id,  :integer
    end

    execute "alter table hardware_resource_groups add constraint fk_hr_group_supergroup
             foreign key (supergroup_id) references hardware_resource_groups(id)"
  end

  def self.down
    drop_table :hardware_resource_groups
  end
end
