class StorageController < ApplicationController
  def index
    list
    render :action => 'list'
  end

  # GETs should be safe (see http://www.w3.org/2001/tag/doc/whenToUseGet.html)
  verify :method => :post, :only => [ :destroy, :create, :update ],
         :redirect_to => { :action => :list }

  def set_perms(hwgroup)
    @user = get_login_user
    @is_admin = hwgroup.is_admin(@user)
    @can_monitor = hwgroup.can_monitor(@user)
    @can_delegate = hwgroup.can_delegate(@user)
  end

  def list
    @attach_to_group=params[:attach_to_group]
    @attach_to_vm=params[:attach_to_vm]
    if @attach_to_group
      group = HardwareResourceGroup.find(@attach_to_group)
      set_perms(group)
      unless @can_monitor
        flash[:notice] = 'You do not have permission to view this storage volume list: redirecting to top level'
        redirect_to :controller => 'pool', :action => 'list'
      else
        conditions = "hardware_resource_group_id is null"
        conditions += " or hardware_resource_group_id=#{group.supergroup_id}" if group.supergroup
        @storage_volumes = StorageVolume.find(:all, :conditions => conditions)
      end
    elsif @attach_to_vm
      vm = Vm.find(@attach_to_vm)
      set_perms(vm.hardware_resource_group)
      unless @can_monitor
        flash[:notice] = 'You do not have permission to view this storage volume list: redirecting to top level'
        redirect_to :controller => 'quota', :action => 'list'
      else
        @storage_volumes = StorageVolume.find(:all, :conditions => "hardware_resource_group_id=#{vm.hardware_resource_group_id}")
      end
    else
      #no permissions here yet -- do we disable raw volume list
      @storage_volumes = StorageVolume.find(:all)
    end
  end

  def show
    @storage_volume = StorageVolume.find(params[:id])
    set_perms(@storage_volume.hardware_resource_group)
    unless @can_monitor
      flash[:notice] = 'You do not have permission to view this storage volume: redirecting to top level'
      redirect_to :controller => 'pool', :action => 'list'
    end
  end

  def new
    @storage_volume = StorageVolume.new({ :hardware_resource_group_id => params[:hardware_resource_group_id] })
    set_perms(@storage_volume.hardware_resource_group)
    unless @is_admin
      flash[:notice] = 'You do not have permission to create this storage volume'
      redirect_to :controller => 'pool', :action => 'show', :id => @storage_volume.hardware_resource_group
    end
  end

  def create
    @storage_volume = StorageVolume.new(params[:storage_volume])
    set_perms(@storage_volume.hardware_resource_group)
    unless @is_admin
      flash[:notice] = 'You do not have permission to create this storage volume'
      redirect_to :controller => 'pool', :action => 'show', :id => @storage_volume.hardware_resource_group
    else
      if @storage_volume.save
        storage_url = url_for(:controller => "storage", :action => "show", :id => @storage_volume)
        flash[:notice] = '<a class="show" href="%s">%s</a> was successfully created.' % [ storage_url ,@storage_volume.ip_addr]
        redirect_to :controller => 'pool', :action => 'show', :id => @storage_volume.hardware_resource_group_id
      else
        render :action => 'new'
      end
    end
  end

  def edit
    @storage_volume = StorageVolume.find(params[:id])
    set_perms(@storage_volume.hardware_resource_group)
    unless @is_admin
      flash[:notice] = 'You do not have permission to edit this storage volume'
      redirect_to :action => 'show', :id => @storage_volume
    end
  end

  def update
    @storage_volume = StorageVolume.find(params[:id])
    set_perms(@storage_volume.hardware_resource_group)
    unless @is_admin
      flash[:notice] = 'You do not have permission to edit this storage volume'
      redirect_to :action => 'show', :id => @storage_volume
    else
      if @storage_volume.update_attributes(params[:storage_volume])
        storage_url = url_for(:controller => "storage", :action => "show", :id => @storage_volume)
        flash[:notice] = '<a class="show" href="%s">%s</a> was successfully updated.' % [ storage_url ,@storage_volume.ip_addr]
        redirect_to :action => 'show', :id => @storage_volume
      else
        render :action => 'edit'
      end
    end
  end

  def destroy
    @storage_volume = StorageVolume.find(params[:id])
    set_perms(@storage_volume.hardware_resource_group)
    unless @is_admin
      flash[:notice] = 'You do not have permission to delete this storage volume'
      redirect_to :action => 'show', :id => @storage_volume
    else
      pool = @storage_volume.hardware_resource_group_id
      @storage_volume.destroy
      redirect_to :controller => 'pool', :action => 'show', :id => pool
    end
  end

  def attach_to_group
    @storage_volume = StorageVolume.find(params[:id])
    set_perms(@storage_volume.hardware_resource_group)
    unless @is_admin
      flash[:notice] = 'You do not have permission to edit this storage volume'
      redirect_to :action => 'show', :id => @host
    else
      group = HardwareResourceGroup.find(params[:hardware_resource_group_id])
      storage_url = url_for(:controller => "storage", :action => "show", :id => @storage_volume)
      group_url = url_for(:controller => "hardware_resource_group", :action => "show", :id => group)
      @storage_volume.hardware_resource_group_id = group.id
      if @storage_volume.save
        flash[:notice] = '<a class="show" href="%s">%s</a> is attached to <a href="%s">%s</a>.' %  [ storage_url ,@storage_volume.ip_addr, group_url, group.name ]
        redirect_to :controller => 'pool', :action => 'show', :id => group
      else
        flash[:notice] = 'Problem attaching <a class="show" href="%s">%s</a> to <a href="%s">%s</a>.' %  [ storage_url ,@storage_volume.ip_addr, host_url, host.hostname ]
        redirect_to :controller => 'pool', :action => 'show', :id => group
      end
    end
  end

  def remove_from_host
    @storage_volume = StorageVolume.find(params[:id])
    set_perms(@storage_volume.hardware_resource_group)
    unless @is_admin
      flash[:notice] = 'You do not have permission to edit this storage volume'
      redirect_to :action => 'show', :id => @host
    else
      host = Host.find(params[:host_id])
      storage_url = url_for(:controller => "storage", :action => "show", :id => @storage_volume)
      host_url = url_for(:controller => "host", :action => "show", :id => host)
      if @storage_volume.hosts.include?(host)
        if @storage_volume.hosts.delete(host)
          flash[:notice] = '<a class="show" href="%s">%s</a> is removed from <a href="%s">%s</a>.' %[ storage_url ,@storage_volume.ip_addr, host_url, host.hostname ]
          redirect_to :controller => 'host', :action => 'show', :id => host
        else
          flash[:notice] = 'Problem attaching <a class="show" href="%s">%s</a> to <a href="%s">%s</a>.' % [ storage_url ,@storage_volume.ip_addr, host_url, host.hostname ]
          redirect_to :controller => 'host', :action => 'show', :id => host
        end
      else
        flash[:notice] = '<a class="show" href="%s">%s</a> is not attached to <a href="%s">%s</a>.' % [ storage_url ,@storage_volume.ip_addr, host_url, host.hostname ]
        redirect_to :controller => 'host', :action => 'show', :id => host
      end
    end
  end
end
