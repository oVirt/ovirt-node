class LibraryController < ApplicationController
  def index
    list
    render :action => 'list'
  end

  # GETs should be safe (see http://www.w3.org/2001/tag/doc/whenToUseGet.html)
  verify :method => :post, :only => [ :destroy, :create, :update ],
         :redirect_to => { :action => :list }

  def list
    @user = get_login_user
    @vm_libraries = VmLibrary.list_for_user(@user)
    @vms = Set.new
    @vm_libraries.each { |vm_library| @vms += vm_library.vms}
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
    @vm_library = VmLibrary.find(params[:id])
    set_perms(@vm_library)
    @is_hwpool_admin = @vm_library.hardware_pool.is_admin(@user)
    @action_values = [["Suspend", Task::ACTION_SUSPEND_VM],
                      ["Resume", Task::ACTION_RESUME_VM],
                      ["Save", Task::ACTION_SAVE_VM],
                      ["Restore", Task::ACTION_RESTORE_VM]]
    unless @can_monitor
      flash[:notice] = 'You do not have permission to view this VM library: redirecting to top level'
      redirect_to :action => 'list'
    end
                      
  end

  def new
    @vm_library = VmLibrary.new( { :hardware_pool_id => params[:hardware_pool] } )
    set_perms(@vm_library.hardware_pool)
    unless @is_admin
      flash[:notice] = 'You do not have permission to create a VM library '
      redirect_to :controller => 'pool', :action => 'show', :id => @vm_library.hardware_pool
    end
  end

  def create
    @vm_library = VmLibrary.new(params[:vm_library])
    set_perms(@vm_library.hardware_pool)
    unless @is_admin
      flash[:notice] = 'You do not have permission to create a VM library '
      redirect_to :controller => 'pool', :action => 'show', :id => @vm_library.hardware_pool
    else
      if @vm_library.save
        flash[:notice] = 'VM Library was successfully created.'
        redirect_to :controller => 'pool', :action => 'show', :id => @vm_library.hardware_pool
      else
        render :action => 'new'
      end
    end
  end

  def edit
    @vm_library = VmLibrary.find(params[:id])
    set_perms(@vm_library.hardware_pool)
    unless @is_admin
      flash[:notice] = 'You do not have permission to edit this VM library '
      redirect_to :action => 'show', :id => @vm_library
    end
  end

  def update
    @vm_library = VmLibrary.find(params[:id])
    set_perms(@vm_library.hardware_pool)
    unless @is_admin
      flash[:notice] = 'You do not have permission to edit this VM library '
      redirect_to :action => 'show', :id => @vm_library
    else
      if @vm_library.update_attributes(params[:vm_library])
        flash[:notice] = 'VM Library was successfully updated.'
        redirect_to :action => 'show', :id => @vm_library
      else
        render :action => 'edit'
      end
    end
  end

  def destroy
    @vm_library = VmLibrary.find(params[:id])
    set_perms(@vm_library.hardware_pool)
    unless @is_admin
      flash[:notice] = 'You do not have permission to delete this VM library '
      redirect_to :action => 'show', :id => @vm_library
    else
      pool_id = @vm_library.hardware_pool_id
      @vm_library.destroy
      redirect_to :controller => 'pool', :action => 'show', :id => pool_id
    end
  end

  def vm_actions
    @vm_library = VmLibrary.find(params[:vm_library_id])
    set_perms(@vm_library)
    unless @is_admin
      flash[:notice] = 'You do not have permission to perform VM actions for this VM library '
      redirect_to :action => 'show', :id => @vm_library
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
      if params[:vm_actions][:vm_library_id]
        redirect_to :action => 'show', :id => params[:vm_actions][:vm_library_id]
      else
        redirect_to :action => 'list'
      end
    end
  end
end
