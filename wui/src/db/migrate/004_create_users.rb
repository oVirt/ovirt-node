class CreateUsers < ActiveRecord::Migration
  def self.up
    create_table :users do |t|
      t.column :ldap_uid,     :string
    end
  end

  def self.down
    drop_table :users
  end
end
