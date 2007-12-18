class PoolController < ApplicationController
  def index
    list
    render :action => 'list'
  end

  # GETs should be safe (see http://www.w3.org/2001/tag/doc/whenToUseGet.html)
  verify :method => :post, :only => [ :destroy, :create, :update ],
         :redirect_to => { :action => :list }

  def list
    @hardware_resource_groups = HardwareResourceGroup.list_for_user(get_login_user)
    @hosts = Set.new
    @storage_volumes = Set.new
    @hardware_resource_groups.each do |group|
      @hosts += group.hosts
      @storage_volumes += group.storage_volumes
    end
    @hosts = @hosts.entries
    @storage_volumes = @storage_volumes.entries
    #what about unattached hosts?
  end

  def show
    @hardware_resource_group = HardwareResourceGroup.find(params[:id])
  end

  def new
    @hardware_resource_group = HardwareResourceGroup.new( { :supergroup_id => params[:supergroup] } )
  end

  def create
    @hardware_resource_group = HardwareResourceGroup.new(params[:hardware_resource_group])
    if @hardware_resource_group.save
      flash[:notice] = 'HardwareResourceGroup was successfully created.'
      redirect_to :action => 'list'
    else
      render :action => 'new'
    end
  end

  def edit
    @hardware_resource_group = HardwareResourceGroup.find(params[:id])
  end

  def update
    @hardware_resource_group = HardwareResourceGroup.find(params[:id])
    if @hardware_resource_group.update_attributes(params[:hardware_resource_group])
      flash[:notice] = 'HardwareResourceGroup was successfully updated.'
      redirect_to :action => 'show', :id => @hardware_resource_group
    else
      render :action => 'edit'
    end
  end

  # move group associations upward upon delete
  def destroy
    group = HardwareResourceGroup.find(params[:id])
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
    end
    HardwareResourceGroup.find(params[:id]).destroy
    redirect_to :action => 'list'
  end
end
