class CreateTasks < ActiveRecord::Migration
  def self.up
    create_table :tasks do |t|
      t.column :user_id,           :integer
      t.column :vm_id,             :integer
      t.column :action,            :string
      t.column :state,             :string
      t.column :args,              :string
      t.column :time_started,      :timestamp
      t.column :time_ended,        :timestamp
    end
    execute "alter table tasks add constraint fk_tasks_users
             foreign key (user_id) references users(id)"
    execute "alter table tasks add constraint fk_tasks_vms
             foreign key (vm_id) references vms(id)"
  end

  def self.down
    drop_table :tasks
  end
end
