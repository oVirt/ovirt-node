class StorageController < ApplicationController
  def index
    list
    render :action => 'list'
  end

  # GETs should be safe (see http://www.w3.org/2001/tag/doc/whenToUseGet.html)
  verify :method => :post, :only => [ :destroy, :create, :update ],
         :redirect_to => { :action => :list }

  def list
    @storage_volume_pages, @storage_volumes = paginate :storage_volumes, :per_page => 10
  end

  def show
    @storage_volume = StorageVolume.find(params[:id])
  end

  def new
    @storage_volume = StorageVolume.new
  end

  def create
    @storage_volume = StorageVolume.new(params[:storage_volume])
    if @storage_volume.save
      flash[:notice] = 'StorageVolume was successfully created.'
      redirect_to :action => 'list'
    else
      render :action => 'new'
    end
  end

  def edit
    @storage_volume = StorageVolume.find(params[:id])
  end

  def update
    @storage_volume = StorageVolume.find(params[:id])
    if @storage_volume.update_attributes(params[:storage_volume])
      flash[:notice] = 'StorageVolume was successfully updated.'
      redirect_to :action => 'show', :id => @storage_volume
    else
      render :action => 'edit'
    end
  end

  def destroy
    StorageVolume.find(params[:id]).destroy
    redirect_to :action => 'list'
  end
end
