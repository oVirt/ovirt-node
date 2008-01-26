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
    @default_pool = HardwarePool.get_default_pool
    set_perms(@default_pool)
    @hardware_pools = HardwarePool.list_for_user(@user)
    @hosts = Set.new
    @storage_volumes = Set.new
    @hardware_pools.each do |pool|
      @hosts += pool.hosts
      @storage_volumes += pool.storage_volumes
    end
    @hosts = @hosts.entries
    @storage_volumes = @storage_volumes.entries
  end

  def set_perms(hwpool)
    @user = get_login_user
    @is_admin = hwpool.is_admin(@user)
    @can_monitor = hwpool.can_monitor(@user)
    @can_delegate = hwpool.can_delegate(@user)
  end

  def show
    @hardware_pool = HardwarePool.find(params[:id])
    set_perms(@hardware_pool)
    unless @can_monitor
      flash[:notice] = 'You do not have permission to view this hardware resource pool: redirecting to top level'
      redirect_to :action => 'list'
    end
  end

  def new
    if not params[:superpool]
      flash[:notice] = 'Parent pool is required for new HardwarePool '
      redirect_to :action => 'list'
    elsif not (params[:is_organizational] or 
               params[:is_network_map] or 
               params[:is_host_collection])
      flash[:notice] = 'Pool type is required for new HardwarePool '
      redirect_to :action => 'list'
    else

      @hardware_pool = HardwarePool.new( { :superpool_id => params[:superpool],
                                         :is_organizational => params[:is_organizational],
                                         :is_network_map => params[:is_network_map],
                                         :is_host_collection => params[:is_host_collection]} )
      set_perms(@hardware_pool.superpool)
      unless @is_admin
        flash[:notice] = 'You do not have permission to create a subpool '
        redirect_to :action => 'show', :id => @hardware_pool.superpool_id
      end
    end
  end

  def create
    if not params[:hardware_pool][:superpool_id]
      flash[:notice] = 'Parent pool is required for new HardwarePool '
      redirect_to :action => 'list'
    elsif not (params[:hardware_pool][:is_organizational] or 
               params[:hardware_pool][:is_network_map] or 
               params[:hardware_pool][:is_host_collection])
      flash[:notice] = 'Pool type is required for new HardwarePool '
      redirect_to :action => 'list'
    else
      @hardware_pool = HardwarePool.new(params[:hardware_pool])
      set_perms(@hardware_pool.superpool)
      unless @is_admin
        flash[:notice] = 'You do not have permission to create a subpool '
        redirect_to :action => 'show', :id => @hardware_pool.superpool_id
      else
        if @hardware_pool.save
          flash[:notice] = 'HardwarePool was successfully created.'
          if @hardware_pool.superpool
            redirect_to :action => 'show', :id => @hardware_pool.superpool_id
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
    @hardware_pool = HardwarePool.find(params[:id])
    set_perms(@hardware_pool)
    unless @is_admin
      flash[:notice] = 'You do not have permission to edit this pool '
      redirect_to :action => 'show', :id => @hardware_pool
    end
  end

  def update
    @hardware_pool = HardwarePool.find(params[:id])
    set_perms(@hardware_pool)
    unless @is_admin
      flash[:notice] = 'You do not have permission to edit this pool '
      redirect_to :action => 'show', :id => @hardware_pool
    else
      if @hardware_pool.update_attributes(params[:hardware_pool])
        flash[:notice] = 'HardwarePool was successfully updated.'
        redirect_to :action => 'show', :id => @hardware_pool
      else
        render :action => 'edit'
      end
    end
  end

  def make_pool
    set_pool_type("is_organizational", 1, "Organizational Pool")
  end
  def unset_pool
    set_pool_type("is_organizational", nil, "Organizational Pool")
  end
  def make_map
    set_pool_type("is_network_map", 1, "Network Map")
  end
  def unset_map
    set_pool_type("is_network_map", nil, "Network Map")
  end
  def make_collection
    set_pool_type("is_host_collection", 1, "Host Collection")
  end
  def unset_collection
    set_pool_type("is_host_collection", nil, "Host Collection")
  end

  def set_pool_type(method,val, label)
    @hardware_pool = HardwarePool.find(params[:id])
    set_perms(@hardware_pool)
    if (not @is_admin)
      flash[:notice] = 'You do not have permission to edit this pool '
    elsif (not @hardware_pool.is_type_update_ok?(method, val))
      operation = val.nil? ? "clear" : "set"
      flash[:notice] = "#{operation}  #{label} is not a valid operation."
    elsif @hardware_pool.send(method) == val
      operation = val.nil? ? "cleared" : "set"
      flash[:notice] = "Pool type #{label} is already #{operation}."
    else
      @hardware_pool.send(method+"=", val)
      operation = val.nil? ? "clear" : "set"
      if @hardware_pool.save
        flash[:notice] = "Pool type #{operation}: #{label}."
      else
        flash[:notice] = "#{operation} #{label} failed."
      end
    end
    redirect_to :action => 'show', :id => @hardware_pool
  end

  # move pool associations upward upon delete
  def destroy
    pool = HardwarePool.find(params[:id])
    set_perms(pool)
    unless @is_admin
      flash[:notice] = 'You do not have permission to destroy this pool '
      redirect_to :action => 'show', :id => pool
    else
      superpool = pool.superpool
      if superpool
        pool.hosts.each do |host| 
          host.hardware_pool_id=superpool.id
          host.save
        end
        pool.storage_volumes.each do |vol| 
          vol.hardware_pool_id=superpool.id
          vol.save
        end
        pool.subpools.each do |subpool| 
          subpool.superpool_id=superpool.id
          subpool.save
        end
        # what about quotas -- for now they're deleted
        HardwarePool.find(params[:id]).destroy
        redirect_to :action => 'show', :id => superpool
      else
        flash[:notice] = "You can't delete the top level HW pool."
        redirect_to :action => 'show', :id => pool
      end
    end
  end
end
