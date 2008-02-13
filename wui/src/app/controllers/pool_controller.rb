class PoolController < AbstractPoolController
  def index
    list
    render :action => 'list'
  end

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


  def new
    @organizational_pools = OrganizationalPool.find(:all)
  end

  def create
    if @organizational_pool.save
      flash[:notice] = 'HardwarePool was successfully created.'
      redirect_to :action => 'show', :id => @organizational_pool
    else
      render :action => 'new'
    end
  end

  def edit
    @other_pools = OrganizationalPool.find(:all, :conditions => [ "id != ?", params[:id] ])
  end

  def update
    if @organizational_pool.update_attributes(params[:organizational_pool])
      flash[:notice] = 'Hardware Pool was successfully updated.'
      redirect_to :action => 'show', :id => @organizational_pool
    else
      render :action => 'edit'
    end
  end

  # pool must be have no subpools empty to delete
  def destroy
    superpool = @organizational_pool.superpool
    if not(superpool)
      flash[:notice] = "You can't delete the top level HW pool."
      redirect_to :action => 'show', :id => @organizational_pool
    elsif not(@organizational_pool.network_maps.empty?)
      flash[:notice] = "You can't delete a pool without first deleting its Network Maps."
      redirect_to :action => 'show', :id => @organizational_pool
    else
      @organizational_pool.move_contents_and_destroy
      redirect_to :controller => "dashboard"
    end
  end

  private
  #filter methods
  def pre_new
    @organizational_pool = OrganizationalPool.new( { :superpool_id => params[:superpool_id] } )
    @perm_obj = @organizational_pool.superpool
  end
  def pre_create
    @organizational_pool = OrganizationalPool.create(params[:organizational_pool])
    @perm_obj = @organizational_pool.superpool
  end
  def pre_edit
    @organizational_pool = OrganizationalPool.find(params[:id])
    @perm_obj = @organizational_pool
  end
  def pre_show
    @organizational_pool = OrganizationalPool.find(params[:id])
    @perm_obj = @organizational_pool
  end
end
