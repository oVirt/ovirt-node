class ConsumerController < ApplicationController
  def index
    @user = User.find(:first, :conditions => [ "ldap_uid = ?", get_login_user])
    @action_values = [["Suspend", Task::ACTION_SUSPEND_VM],
                      ["Resume", Task::ACTION_RESUME_VM],
                      ["Save", Task::ACTION_SAVE_VM],
                      ["Restore", Task::ACTION_RESTORE_VM]]
                      
    if @user
      @quota = @user.user_quota
    else
      @quota = nil
    end
  end

  def vm_actions
    params[:vm_actions].each do |name, param|
      print "param: ", name, ", ", param, "\n"
    end
    if params[:vm_actions][:vms]
      vms = params[:vm_actions][:vms]
      if params[:vm_actions][Task::ACTION_START_VM]
        flash[:notice] = "Starting Machines #{vms.join(',')}."
      elsif params[:vm_actions][Task::ACTION_SHUTDOWN_VM]
        flash[:notice] = "Stopping Machines #{vms.join(',')}."
      elsif params[:vm_actions][:other_actions]
        case params[:vm_actions][:other_actions]
        when Task::ACTION_SHUTDOWN_VM then flash[:notice] = "Stopping Machines #{vms.join(',')}."
        when Task::ACTION_START_VM then flash[:notice] = "Starting Machines #{vms.join(',')}."
        when Task::ACTION_SUSPEND_VM then flash[:notice] = "Suspending Machines #{vms.join(',')}."
        when Task::ACTION_RESUME_VM then flash[:notice] = "Resuming Machines #{vms.join(',')}."
        when Task::ACTION_SAVE_VM then flash[:notice] = "Saving Machines #{vms.join(',')}."
        when Task::ACTION_RESTORE_VM then flash[:notice] = "Restoring Machines #{vms.join(',')}."
        when "destroy" then flash[:notice] = "Destroying Machines #{vms.join(',')}."
        else
          flash[:notice] = 'No Action Chosen.'
        end
      else
        flash[:notice] = 'No Action Chosen.'
      end
    else
        flash[:notice] = 'No Virtual Machines Selected.'
    end
    redirect_to :action => 'index'
  end
end
