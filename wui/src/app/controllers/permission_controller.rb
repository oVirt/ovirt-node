class PermissionController < ApplicationController
  def index
    list
    render :action => 'list'
  end

  # GETs should be safe (see http://www.w3.org/2001/tag/doc/whenToUseGet.html)
  verify :method => :post, :only => [ :destroy, :create, :update ],
         :redirect_to => { :action => :list }

  def list
    @permission_pages, @permissions = paginate :permissions, :per_page => 10
  end

  def show
    @permission = Permission.find(params[:id])
  end

  def new
    @permission = Permission.new
  end

  def create
    @permission = Permission.new(params[:permission])
    if @permission.save
      flash[:notice] = 'Permission was successfully created.'
      redirect_to :action => 'list'
    else
      render :action => 'new'
    end
  end

  def edit
    @permission = Permission.find(params[:id])
  end

  def update
    @permission = Permission.find(params[:id])
    if @permission.update_attributes(params[:permission])
      flash[:notice] = 'Permission was successfully updated.'
      redirect_to :action => 'show', :id => @permission
    else
      render :action => 'edit'
    end
  end

  def destroy
    Permission.find(params[:id]).destroy
    redirect_to :action => 'list'
  end
end
