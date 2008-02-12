class NetworkMapController < AbstractPoolController

  def new
    @organizational_pool = OrganizationalPool.find(params[:superpool_id])
  end

  def create
    if @network_map.save
      flash[:notice] = 'Network Map successfully created'
      redirect_to  :controller => 'network_map', :action => 'show', :id => @network_map
    else
      render :action => "new"
    end
  end

  def update
    if @network_map.update_attributes(params[:network_map])
      flash[:notice] = 'Network Map was successfully updated.'
      redirect_to  :controller => 'network_map', :action => 'show', :id => @network_map
    else
      render :action => "edit"
    end
  end

  def destroy
    superpool = @network_map.superpool
    unless(@network_map.host_collections.empty?)
      flash[:notice] = "You can't delete a Network Map without first deleting its Collections."
      redirect_to :action => 'show', :id => @network_map
    else
      move_contents_and_destory(@network_map)
      flash[:notice] = 'Network Map successfully destroyed'
      redirect_to :controller => 'pool', :action => 'show', :id => @network_map.organizational_pool
    end
  end

  private
  #filter methods
  def pre_new
    @network_map = NetworkMap.new( { :superpool_id => params[:superpool_id] } )
    @perm_pool = @network_map.superpool
  end
  def pre_create
    @network_map = NetworkMap.create(params[:network_map])
    @perm_pool = @network_map.superpool
  end
  def pre_edit
    @network_map = NetworkMap.find(params[:id])
    @perm_pool = @network_map
  end
end
