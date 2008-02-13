class CollectionController < AbstractPoolController

  def new
    if @collection.network_map
      @collections = @collection.network_map.host_collections
    else
      @collections = @collection.parent_collection.host_collections
    end
  end

  def create
    if @collection.save
      flash[:notice] = 'Host Collection successfully created'
      redirect_to  :controller => 'collection', :action => 'show', :id => @collection
    else
      render :action => "new"
    end
  end

  def update
    if @collection.update_attributes(params[:collection])
      flash[:notice] = 'Host Collection was successfully updated.'
      redirect_to  :controller => 'collection', :action => 'show', :id => @collection
    else
      render :action => "edit"
    end
  end

  def destroy
    superpool = @collection.superpool
    unless(@collection.host_collections.empty?)
      flash[:notice] = "You can't delete a Collection without first deleting its Subollections."
      redirect_to :action => 'show', :id => @collection
    else
      @collection.move_contents_and_destroy
      flash[:notice] = 'Host Collection successfully destroyed'
      redirect_to :controller => 'pool', :action => 'show', :id => @collection.organizational_pool
      if superpool[:type] == NetworkMap.name
        redirect_to :controller => 'network_map', :action => 'show', :id => @collection.network_map
      else
        redirect_to :controller => 'collection', :action => 'show', :id => @collection.superpool_id
      end
    end
  end

  private
  #filter methods
  def pre_new
    @collection = HostCollection.new( { :superpool_id => params[:superpool_id] } )
    @perm_obj = @collection.superpool
  end
  def pre_create
    @collection = HostCollection.create(params[:collection])
    @perm_obj = @collection.superpool
  end
  def pre_edit
    @collection = HostCollection.find(params[:id])
    @perm_obj = @collection
  end
  def pre_show
    @collection = HostCollection.find(params[:id])
    @perm_obj = @collection
  end
end
