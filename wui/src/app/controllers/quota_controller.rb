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

  def set_perms(perm_obj)
    @user = get_login_user
    @is_admin = perm_obj.is_admin(@user)
    @can_monitor = perm_obj.can_monitor(@user)
    @can_delegate = perm_obj.can_delegate(@user)
  end

  def show
    @quota = Quota.find(params[:id])
    set_perms(@quota)
    @is_hwpool_admin = @quota.hardware_pool.is_admin(@user)
    @action_values = [["Suspend", Task::ACTION_SUSPEND_VM],
                      ["Resume", Task::ACTION_RESUME_VM],
                      ["Save", Task::ACTION_SAVE_VM],
                      ["Restore", Task::ACTION_RESTORE_VM]]
    unless @can_monitor
      flash[:notice] = 'You do not have permission to view this quota: redirecting to top level'
      redirect_to :action => 'list'
    end
                      
  end

  def new
    @quota = Quota.new( { :hardware_pool_id => params[:hardware_pool] } )
    set_perms(@quota.hardware_pool)
    unless @is_admin
      flash[:notice] = 'You do not have permission to create a quota '
      redirect_to :controller => 'pool', :action => 'show', :id => @quota.hardware_pool
    end
  end

  def create
    @quota = Quota.new(params[:quota])
    set_perms(@quota.hardware_pool)
    unless @is_admin
      flash[:notice] = 'You do not have permission to create a quota '
      redirect_to :controller => 'pool', :action => 'show', :id => @quota.hardware_pool
    else
      if @quota.save
        flash[:notice] = 'Quota was successfully created.'
        redirect_to :controller => 'pool', :action => 'show', :id => @quota.hardware_pool
      else
        render :action => 'new'
      end
    end
  end

  def edit
    @quota = Quota.find(params[:id])
    set_perms(@quota.hardware_pool)
    unless @is_admin
      flash[:notice] = 'You do not have permission to edit this quota '
      redirect_to :action => 'show', :id => @quota
    end
  end

  def update
    @quota = Quota.find(params[:id])
    set_perms(@quota.hardware_pool)
    unless @is_admin
      flash[:notice] = 'You do not have permission to edit this quota '
      redirect_to :action => 'show', :id => @quota
    else
      if @quota.update_attributes(params[:quota])
        flash[:notice] = 'Quota was successfully updated.'
        redirect_to :action => 'show', :id => @quota
      else
        render :action => 'edit'
      end
    end
  end

  def destroy
    @quota = Quota.find(params[:id])
    set_perms(@quota.hardware_pool)
    unless @is_admin
      flash[:notice] = 'You do not have permission to delete this quota '
      redirect_to :action => 'show', :id => @quota
    else
      pool_id = @quota.hardware_pool_id
      @quota.destroy
      redirect_to :controller => 'pool', :action => 'show', :id => pool_id
    end
  end

  def vm_actions
    @quota = Quota.find(params[:quota_id])
    set_perms(@quota)
    unless @is_admin
      flash[:notice] = 'You do not have permission to perform VM actions for this quota '
      redirect_to :action => 'show', :id => @quota
    else
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
end
