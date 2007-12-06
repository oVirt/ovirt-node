class VmController < ApplicationController
  def index
    list
    render :action => 'list'
  end

  # GETs should be safe (see http://www.w3.org/2001/tag/doc/whenToUseGet.html)
  verify :method => :post, :only => [ :destroy, :create, :update ],
         :redirect_to => { :action => :list }

  def list
    @vm_pages, @vms = paginate :vms, :per_page => 10
  end

  def show
    @vm = Vm.find(params[:id])
    @actions = @vm.get_action_and_label_list
  end

  def new
    # random MAC
    mac = [ 0x00, 0x16, 0x3e, rand(0x7f), rand(0xff), rand(0xff) ]
    # random uuid
    uuid = ["%02x" * 4, "%02x" * 2, "%02x" * 2, "%02x" * 2, "%02x" * 6].join("-") % 
      Array.new(16) {|x| rand(0xff) }
    newargs = { 
      :user_id => params[:user_id],
      :vnic_mac_addr => mac.collect {|x| "%02x" % x}.join(":"),
      :uuid => uuid
    }
    @vm = Vm.new( newargs )
  end

  def create
    params[:vm][:state] = Vm::STATE_PENDING
    @vm = Vm.new(params[:vm])
    user = get_login_user_id
    if @vm.save
      @task = Task.new({ :user_id => user.id,
                         :vm_id   => @vm.id,
                         :action  => Task::ACTION_CREATE_VM,
                         :state   => Task::STATE_QUEUED})
      if @task.save
        flash[:notice] = 'Vm was successfully created.'
      else
        flash[:notice] = 'Error in inserting task.'
      end
      redirect_to :controller => 'consumer', :action => 'index'
    else
      render :action => 'new'
    end
  end

  def edit
    @vm = Vm.find(params[:id])
  end

  def update
    @vm = Vm.find(params[:id])
    #needs restart if certain fields are changed (since those will only take effect the next startup)
    needs_restart = false
    needs_new_storage_ids = false
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
    unless current_storage_ids == new_storage_ids
      needs_new_storage_ids = true 
      needs_restart = true
    end
    params[:vm][:needs_restart] = 1 if needs_restart
    if @vm.update_attributes(params[:vm])
      flash[:notice] = 'Vm was successfully updated.'
      redirect_to :controller => 'consumer', :action => 'index'
    else
      render :action => 'edit'
    end
  end

  def destroy
    @vm = Vm.find(params[:id])
    @vm.destroy
    redirect_to :controller => 'consumer', :action => 'index'
  end

  def vm_action
    @vm = Vm.find(params[:id])
    if @vm.get_action_list.include?(params[:vm_action])
      @task = Task.new({ :user_id => get_login_user_id.id,
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

  def cancel_queued_tasks
    @vm = Vm.find(params[:id])
    @vm.get_queued_tasks.each { |task| task.cancel}
    flash[:notice] = "queued tasks canceled."
    redirect_to :controller => 'vm', :action => 'show', :id => params[:id]
  end
end
