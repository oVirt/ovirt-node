class PoolController < ApplicationController
  def index
    list
    render :action => 'list'
  end

  # GETs should be safe (see http://www.w3.org/2001/tag/doc/whenToUseGet.html)
  verify :method => :post, :only => [ :destroy, :create, :update ],
         :redirect_to => { :action => :list }

  def list
    @hardware_resource_group_pages, @hardware_resource_groups = paginate :hardware_resource_groups, :per_page => 10
  end

  def show
    @hardware_resource_group = HardwareResourceGroup.find(params[:id])
  end

  def new
    @hardware_resource_group = HardwareResourceGroup.new
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

  def destroy
    HardwareResourceGroup.find(params[:id]).destroy
    redirect_to :action => 'list'
  end
end
