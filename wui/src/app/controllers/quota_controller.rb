class QuotaController < ApplicationController
  def index
    list
    render :action => 'list'
  end

  # GETs should be safe (see http://www.w3.org/2001/tag/doc/whenToUseGet.html)
  verify :method => :post, :only => [ :destroy, :create, :update ],
         :redirect_to => { :action => :list }

  def list
    @user = get_login_user
    @quotas = Quota.list_for_user(@user)
    @vms = Set.new
    @quotas.each { |quota| @vms += quota.vms}
    @vms = @vms.entries
    @action_values = [["Suspend", Task::ACTION_SUSPEND_VM],
                      ["Resume", Task::ACTION_RESUME_VM],
                      ["Save", Task::ACTION_SAVE_VM],
                      ["Restore", Task::ACTION_RESTORE_VM]]
  end

  def show
    @quota = Quota.find(params[:id])
    @user = get_login_user
    @action_values = [["Suspend", Task::ACTION_SUSPEND_VM],
                      ["Resume", Task::ACTION_RESUME_VM],
                      ["Save", Task::ACTION_SAVE_VM],
                      ["Restore", Task::ACTION_RESTORE_VM]]
                      
  end

  def new
    @quota = Quota.new( { :hardware_resource_group_id => params[:hardware_resource_group] } )
  end

  def create
    @quota = Quota.new(params[:quota])
    if @quota.save
      flash[:notice] = 'Quota was successfully created.'
      redirect_to :controller => 'pool', :action => 'show', :id => @quota.hardware_resource_group
    else
      render :action => 'new'
    end
  end

  def edit
    @quota = Quota.find(params[:id])
  end

  def update
    @quota = Quota.find(params[:id])
    if @quota.update_attributes(params[:quota])
      flash[:notice] = 'Quota was successfully updated.'
      redirect_to :action => 'show', :id => @quota
    else
      render :action => 'edit'
    end
  end

  def destroy
    @quota = Quota.find(params[:id])
    group_id = @quota.hardware_resource_group_id
    @quota.destroy
    redirect_to :controller => 'pool', :action => 'show', :id => group_id
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
    if params[:vm_actions][:quota_id]
    redirect_to :action => 'show', :id => params[:vm_actions][:quota_id]
    else
      redirect_to :action => 'list'
    end
  end
end
