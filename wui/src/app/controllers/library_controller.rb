class LibraryController < ApplicationController
  def index
    list
    render :action => 'list'
  end

  # GETs should be safe (see http://www.w3.org/2001/tag/doc/whenToUseGet.html)
  verify :method => :post, :only => [ :destroy, :create, :update ],
         :redirect_to => { :action => :list }

  before_filter :pre_new, :only => [:new]
  before_filter :pre_create, :only => [:create]
  before_filter :pre_show, :only => [:show]
  before_filter :pre_edit, :only => [:edit, :update, :destroy]
  before_filter :authorize_admin, :only => [:new, :create, :edit, :update, :destroy]

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

  def show
    set_perms(@perm_obj)
    @is_hwpool_admin = @vm_library.host_collection.is_admin(@user)
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
  end

  def create
    if @vm_library.save
      flash[:notice] = 'VM Library was successfully created.'
      redirect_to :controller => 'collection', :action => 'show', :id => @vm_library.host_collection
    else
      render :action => 'new'
    end
  end

  def edit
  end

  def update
    if @vm_library.update_attributes(params[:vm_library])
      flash[:notice] = 'VM Library was successfully updated.'
      redirect_to :action => 'show', :id => @vm_library
    else
      render :action => 'edit'
    end
  end

  def destroy
    host_collection_id = @vm_library.host_collection_id
    @vm_library.destroy
    redirect_to :controller => 'collection', :action => 'show', :id => host_collection_id
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

  protected
  def authorize_admin
    set_perms(@perm_obj)
    unless @is_admin
      flash[:notice] = 'You do not have permission to create or modify a library here '
      if @perm_obj.class = HostCollection
        redirect_to :controller => 'collection', :action => 'show', :id => @perm_obj
      else
        redirect_to :action => 'show', :id => @perm_obj
      end
    end
    false
  end
  def pre_new
    @vm_library = VmLibrary.new( { :host_collection_id => params[:host_collection_id] } )
    @perm_obj = @vm_library.host_collection
    @redir_obj = @perm_obj
  end
  def pre_create
    @vm_library = VmLibrary.new(params[:vm_library])
    @perm_obj = @vm_library.host_collection
    @redir_obj = @perm_obj
  end
  def pre_show
    @vm_library = VmLibrary.find(params[:id])
    @perm_obj = @vm_library
  end
  def pre_edit
    @vm_library = VmLibrary.find(params[:id])
    @perm_obj = @vm_library.host_collection
    @redir_obj = @vm_library
  end

end
