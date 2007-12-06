class User < ActiveRecord::Base
  has_one  :user_quota, :dependent => :nullify
  has_many :vms, :dependent => :nullify, :order => "id ASC"
  has_many :tasks, :dependent => :nullify, :order => "id ASC"

  def working_tasks
    tasks_for_states(Task::WORKING_STATES)
  end

  def completed_tasks
    tasks_for_states(Task::COMPLETED_STATES)
  end

  def tasks_for_states(state_array)
    tasks.find(:all, 
               :conditions => state_array.collect {|x| "state='#{x}'"}.join(" or "))
  end
end
