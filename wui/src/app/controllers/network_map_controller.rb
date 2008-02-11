class NetworkMapController < ApplicationController

  def show
    @map = NetworkMap.find(params[:id])
    set_perms(@map)
  end

  def new
    @organizational_pool = OrganizationalPool.find(params[:superpool_id])
    @network_map = NetworkMap.new({ :organizational_pool => @organizational_pool })
  end

  def create
    @network_map = NetworkMap.create(params[:network_map])
    if @network_map.save
      flash[:notice] = 'Network Map successfully created'
      redirect_to  :controller => 'network_map', :action => 'show', :id => @network_map
    else
      render :action => "new"
    end
  end

  def update
    @network_map = NetworkMap.find(params[:id])

    if @network_map.update_attributes(params[:network_map])
      flash[:notice] = 'Network Map was successfully updated.'
      redirect_to  :controller => 'network_map', :action => 'show', :id => @network_map
    else
      render :action => "edit"
    end
  end

  def edit
    @network_map = NetworkMap.find(params[:id])
  end

  def destroy
    @network_map = NetworkMap.find(params[:id])
    @network_map.destroy
    flash[:notice] = 'Network Map successfully destroyed'
    redirect_to :controller => 'pool', :action => 'show', :id => @network_map.organizational_pool
  end
end
