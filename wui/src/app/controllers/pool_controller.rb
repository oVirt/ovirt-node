class PoolController < ApplicationController
  def index
    list
    render :action => 'list'
  end

  # GETs should be safe (see http://www.w3.org/2001/tag/doc/whenToUseGet.html)
  verify :method => :post, :only => [ :destroy, :create, :update ],
         :redirect_to => { :action => :list }

  #FIXME: this method isn't really needed anymore
  def list
    @user = get_login_user
    @default_pool = MotorPool.find(:first)
    set_perms(@default_pool)
    @organizational_pools = OrganizationalPool.list_for_user(@user)
    @hosts = Set.new
    @storage_volumes = Set.new
    @organizational_pools.each do |pool|
      @hosts += pool.hosts
      @storage_volumes += pool.storage_volumes
    end
    @hosts = @hosts.entries
    @storage_volumes = @storage_volumes.entries
  end

  def show
    @organizational_pool = OrganizationalPool.find(params[:id])
    set_perms(@organizational_pool)
    unless @can_monitor
      flash[:notice] = 'You do not have permission to view this hardware resource pool: redirecting to top level'
      redirect_to :action => 'list'
    end
  end

  def new
    @organizational_pools = OrganizationalPool.find(:all)
    @organizational_pool = OrganizationalPool.new( { :superpool_id => params[:superpool] } )
    set_perms(@organizational_pool.superpool)
    unless @is_admin
      flash[:notice] = 'You do not have permission to create a new pool '
      redirect_to :action => 'show', :id => @organizational_pool.superpool_id
    end
  end

  def create
    @organizational_pool = OrganizationalPool.create(params[:organizational_pool])
    @organizational_pool.superpool = MotorPool.find(:first)
    set_perms(@organizational_pool.superpool)
    unless @is_admin
      flash[:notice] = 'You do not have permission to create a subpool '
      redirect_to :action => 'show', :id => @organizational_pool
    else
      if @organizational_pool.save
        flash[:notice] = 'HardwarePool was successfully created.'
        if @organizational_pool.superpool
          redirect_to :action => 'show', :id => @organizational_pool
        else
          redirect_to :action => 'list'
        end
      else
        render :action => 'new'
      end
    end
  end

  def edit
    @other_pools = OrganizationalPool.find(:all, :conditions => [ "id != ?", params[:id] ])
    @organizational_pool = OrganizationalPool.find(params[:id])
    set_perms(@organizational_pool)
    unless @is_admin
      flash[:notice] = 'You do not have permission to edit this pool '
      redirect_to :action => 'show', :id => @organizational_pool
    end
  end

  def update
    @organizational_pool = OrganizationalPool.find(params[:id])
    set_perms(@organizational_pool)
    unless @is_admin
      flash[:notice] = 'You do not have permission to edit this pool '
      redirect_to :action => 'show', :id => @organizational_pool
    else
      if @organizational_pool.update_attributes(params[:organizational_pool])
        flash[:notice] = 'Hardware Pool was successfully updated.'
        redirect_to :action => 'show', :id => @organizational_pool
      else
        render :action => 'edit'
      end
    end
  end

  # pool must be have no subpools empty to delete
  def destroy
    pool = OrganizationalPool.find(params[:id])
    set_perms(pool)
    unless @is_admin
      flash[:notice] = 'You do not have permission to destroy this pool '
      redirect_to :action => 'show', :id => pool
    else
      superpool = pool.superpool
      if not(superpool)
        flash[:notice] = "You can't delete the top level HW pool."
        redirect_to :action => 'show', :id => pool
      elsif not(pool.network_maps.empty?)
        flash[:notice] = "You can't delete a pool without first deleting it's Network Maps."
        redirect_to :action => 'show', :id => pool
      else
        pool.hosts.each do |host| 
          host.hardware_pool_id=superpool.id
          host.save
        end
        pool.storage_volumes.each do |vol| 
          vol.hardware_pool_id=superpool.id
          vol.save
        end
        # what about quotas -- for now they're deleted
        pool.destroy
        redirect_to :controller => "dashboard"
      end
    end
  end
end

