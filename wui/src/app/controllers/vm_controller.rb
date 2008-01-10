class VmController < ApplicationController
  # GETs should be safe (see http://www.w3.org/2001/tag/doc/whenToUseGet.html)
  verify :method => :post, :only => [ :destroy, :create, :update ],
         :redirect_to => { :action => :list }

  def set_perms(perm_obj)
    @user = get_login_user
    @is_admin = perm_obj.is_admin(@user)
    @can_monitor = perm_obj.can_monitor(@user)
    @can_delegate = perm_obj.can_delegate(@user)
  end

  def show
    @vm = Vm.find(params[:id])
    @actions = @vm.get_action_and_label_list
    set_perms(@vm.quota)
    unless @can_monitor
      flash[:notice] = 'You do not have permission to view this vm: redirecting to top level'
      redirect_to :controller => 'quota', :action => 'list'
    end
  end

  def new
    # random MAC
    mac = [ 0x00, 0x16, 0x3e, rand(0x7f), rand(0xff), rand(0xff) ]
    # random uuid
    uuid = ["%02x" * 4, "%02x" * 2, "%02x" * 2, "%02x" * 2, "%02x" * 6].join("-") % 
      Array.new(16) {|x| rand(0xff) }
    newargs = { 
      :quota_id => params[:quota_id],
      :vnic_mac_addr => mac.collect {|x| "%02x" % x}.join(":"),
      :uuid => uuid
    }
    @vm = Vm.new( newargs )
    set_perms(@vm.quota)
    unless @is_admin
      flash[:notice] = 'You do not have permission to create this vm'
      redirect_to :controller => 'quota', :action => 'show', :id => @vm.quota_id
    end
  end

  def create
    params[:vm][:state] = Vm::STATE_PENDING
    @vm = Vm.new(params[:vm])
    set_perms(@vm.quota)
    unless @is_admin
      flash[:notice] = 'You do not have permission to create this vm'
      redirect_to :controller => 'quota', :action => 'show', :id => @vm.quota_id
    else
      if @vm.save
        @task = Task.new({ :user    => @user,
                           :vm_id   => @vm.id,
                           :action  => Task::ACTION_CREATE_VM,
                           :state   => Task::STATE_QUEUED})
        if @task.save
          flash[:notice] = 'Vm was successfully created.'
        else
          flash[:notice] = 'Error in inserting task.'
        end
        redirect_to :controller => 'quota', :action => 'show', :id => @vm.quota
      else
        render :action => 'new'
      end
    end
  end

  def edit
    @vm = Vm.find(params[:id])
    set_perms(@vm.quota)
    unless @is_admin
      flash[:notice] = 'You do not have permission to edit this vm'
      redirect_to :action => 'show', :id => @vm
    end
  end

  def update
    @vm = Vm.find(params[:id])
    set_perms(@vm.quota)
    unless @is_admin
      flash[:notice] = 'You do not have permission to edit this vm'
      redirect_to :action => 'show', :id => @vm
    else
      #needs restart if certain fields are changed (since those will only take effect the next startup)
      needs_restart = false
      unless @vm.get_pending_state == Vm::STATE_STOPPED
        Vm::NEEDS_RESTART_FIELDS.each do |field|
          unless @vm[field].to_s == params[:vm][field]
            needs_restart = true
            break
          end
        end
        current_storage_ids = @vm.storage_volume_ids.sort
        new_storage_ids = params[:vm][:storage_volume_ids]
        new_storage_ids = [] unless new_storage_ids
        new_storage_ids = new_storage_ids.sort.collect {|x| x.to_i }
        needs_restart = true unless current_storage_ids == new_storage_ids
      end
      params[:vm][:needs_restart] = 1 if needs_restart
      if @vm.update_attributes(params[:vm])
        flash[:notice] = 'Vm was successfully updated.'
        redirect_to :action => 'show', :id => @vm
      else
        render :action => 'edit'
      end
    end
  end

  def destroy
    @vm = Vm.find(params[:id])
    set_perms(@vm.quota)
    unless @is_admin
      flash[:notice] = 'You do not have permission to delete this vm'
      redirect_to :action => 'show', :id => @vm
    else
      quota = @vm.quota_id
      if @vm.state == Vm::STATE_STOPPED and @vm.get_pending_state == Vm::STATE_STOPPED
        @vm.destroy
        if quota
          redirect_to :controller => 'quota', :action => 'show', :id => quota
        else
          redirect_to :controller => 'quota', :action => 'list'
        end
      else
        flash[:notice] = "Vm must be stopped to destroy it."
        redirect_to :controller => 'vm', :action => 'show', :id => params[:id]
      end
    end
  end

  def vm_action
    @vm = Vm.find(params[:id])
    set_perms(@vm.quota)
    unless @is_admin
      flash[:notice] = 'You do not have permission to schedule actions for this vm'
      redirect_to :action => 'show', :id => @vm
    else
      if @vm.get_action_list.include?(params[:vm_action])
        @task = Task.new({ :user    => get_login_user,
                           :vm_id   => params[:id],
                           :action  => params[:vm_action],
                           :state   => Task::STATE_QUEUED})
        if @task.save
          flash[:notice] = "#{params[:vm_action]} was successfully queued."
        else
          flash[:notice] = "Error in inserting task for #{params[:vm_action]}."
        end
      else
        flash[:notice] = "#{params[:vm_action]} is an invalid action."
      end
      redirect_to :controller => 'vm', :action => 'show', :id => params[:id]
    end
  end

  def cancel_queued_tasks
    @vm = Vm.find(params[:id])
    set_perms(@vm.quota)
    unless @is_admin
      flash[:notice] = 'You do not have permission to cancel actions for this vm'
      redirect_to :action => 'show', :id => @vm
    else
      @vm.get_queued_tasks.each { |task| task.cancel}
      flash[:notice] = "queued tasks canceled."
      redirect_to :controller => 'vm', :action => 'show', :id => params[:id]
    end
  end
end
