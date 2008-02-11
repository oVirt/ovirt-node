class CollectionController < ApplicationController

  def show
    @collection = HostCollection.find(params[:id])
    set_perms(@collection)
  end

  def new
    @collection = HostCollection.new({ :network_map => NetworkMap.find(params[:superpool_id]) } )
  end

  def create
    @collection = HostCollection.create(params[:collection])
    if @collection.save
      flash[:notice] = 'Host Collection successfully created'
      redirect_to  :controller => 'collection', :action => 'show', :id => @collection
    else
      render :action => "new"
    end
  end

  def update
    @collection = HostCollection.find(params[:id])

    if @collection.update_attributes(params[:collection])
      flash[:notice] = 'Host Collection was successfully updated.'
      redirect_to  :controller => 'collection', :action => 'show', :id => @collection
    else
      render :action => "edit"
    end
  end

  def edit
    @collection = HostCollection.find(params[:id])
  end

  def destroy
    @collection = HostCollection.find(params[:id])
    @collection.destroy
    flash[:notice] = 'Host Collection successfully destroyed'
    redirect_to :controller => 'network_map', :action => 'show', :id => @collection.network_map
  end
end
