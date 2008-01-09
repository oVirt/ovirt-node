class PoolController < ApplicationController
  def index
    list
    render :action => 'list'
  end

  # GETs should be safe (see http://www.w3.org/2001/tag/doc/whenToUseGet.html)
  verify :method => :post, :only => [ :destroy, :create, :update ],
         :redirect_to => { :action => :list }

  def list
    @user = get_login_user
    @default_group = HardwareResourceGroup.get_default_group
    set_perms(@default_group)
    @hardware_resource_groups = HardwareResourceGroup.list_for_user(@user)
    @hosts = Set.new
    @storage_volumes = Set.new
    @hardware_resource_groups.each do |group|
      @hosts += group.hosts
      @storage_volumes += group.storage_volumes
    end
    @hosts = @hosts.entries
    @storage_volumes = @storage_volumes.entries
  end

  def set_perms(hwgroup)
    @user = get_login_user
    @is_admin = hwgroup.is_admin(@user)
    @can_monitor = hwgroup.can_monitor(@user)
    @can_delegate = hwgroup.can_delegate(@user)
  end

  def show
    @hardware_resource_group = HardwareResourceGroup.find(params[:id])
    set_perms(@hardware_resource_group)
    unless @can_monitor
      flash[:notice] = 'You do not have permission to view this hardware resource group: redirecting to top level'
      redirect_to :action => 'list'
    end
  end

  def new
    unless params[:supergroup]
      flash[:notice] = 'Parent group is required for new HardwareResourceGroup '
      redirect_to :action => 'list'
    else
      @hardware_resource_group = HardwareResourceGroup.new( { :supergroup_id => params[:supergroup] } )
      set_perms(@hardware_resource_group.supergroup)
      unless @is_admin
        flash[:notice] = 'You do not have permission to create a subgroup '
        redirect_to :action => 'show', :id => @hardware_resource_group.supergroup_id
      end
    end
  end

  def create
    unless params[:hardware_resource_group][:supergroup_id]
      flash[:notice] = 'Parent group is required for new HardwareResourceGroup '
      redirect_to :action => 'list'
    else
      @hardware_resource_group = HardwareResourceGroup.new(params[:hardware_resource_group])
      set_perms(@hardware_resource_group.supergroup)
      unless @is_admin
        flash[:notice] = 'You do not have permission to create a subgroup '
        redirect_to :action => 'show', :id => @hardware_resource_group.supergroup_id
      else
        if @hardware_resource_group.save
          flash[:notice] = 'HardwareResourceGroup was successfully created.'
          if @hardware_resource_group.supergroup
            redirect_to :action => 'show', :id => @hardware_resource_group.supergroup_id
          else
            redirect_to :action => 'list'
          end
        else
          render :action => 'new'
        end
      end
    end
  end

  def edit
    @hardware_resource_group = HardwareResourceGroup.find(params[:id])
    set_perms(@hardware_resource_group)
    unless @is_admin
      flash[:notice] = 'You do not have permission to edit this group '
      redirect_to :action => 'show', :id => @hardware_resource_group
    end
  end

  def update
    @hardware_resource_group = HardwareResourceGroup.find(params[:id])
    set_perms(@hardware_resource_group)
    unless @is_admin
      flash[:notice] = 'You do not have permission to edit this group '
      redirect_to :action => 'show', :id => @hardware_resource_group
    else
      if @hardware_resource_group.update_attributes(params[:hardware_resource_group])
        flash[:notice] = 'HardwareResourceGroup was successfully updated.'
        redirect_to :action => 'show', :id => @hardware_resource_group
      else
        render :action => 'edit'
      end
    end
  end

  # move group associations upward upon delete
  def destroy
    group = HardwareResourceGroup.find(params[:id])
    set_perms(group)
    unless @is_admin
      flash[:notice] = 'You do not have permission to destroy this group '
      redirect_to :action => 'show', :id => group
    else
      supergroup = group.supergroup
      if supergroup
        group.hosts.each do |host| 
          host.hardware_resource_group_id=supergroup.id
          host.save
        end
        group.storage_volumes.each do |vol| 
          vol.hardware_resource_group_id=supergroup.id
          vol.save
        end
        group.subgroups.each do |subgroup| 
          subgroup.supergroup_id=supergroup.id
          subgroup.save
        end
        # what about quotas -- for now they're deleted
        HardwareResourceGroup.find(params[:id]).destroy
        redirect_to :action => 'show', :id => supergroup
      else
        flash[:notice] = "You can't delete the top level HW group."
        redirect_to :action => 'show', :id => group
      end
    end
  end
end
