class DenormalizePermissions < ActiveRecord::Migration
  def self.up
    add_column :permissions, :inherited_from_id, :integer
    execute "alter table permissions add constraint fk_perm_parent
             foreign key (inherited_from_id) references permissions(id)"

    Permission.transaction do
      Permission.find(:all,
                      :conditions => "inherited_from_id is null"
                      ).each do |permission|
        permission.pool.all_children.each do |subpool|
          new_permission = Permission.new({:pool_id     => subpool.id,
                                           :uid         => permission.uid,
                                           :user_role   => permission.user_role,
                                           :inherited_from_id => permission.id})
          new_permission.save!
        end
      end
    end
  end

  def self.down
    Permission.transaction do
      Permission.find(:all,
                      :conditions => "inherited_from_id is not null"
                      ).each do |permission|
        permission.destroy
      end
    end
    remove_column :permissions, :inherited_from_id
  end
end
