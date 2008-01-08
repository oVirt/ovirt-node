class PermissionController < ApplicationController
  def index
    list
    render :action => 'list'
  end

  # GETs should be safe (see http://www.w3.org/2001/tag/doc/whenToUseGet.html)
  verify :method => :post, :only => [ :destroy, :create, :update ],
         :redirect_to => { :action => :list }

  def list
    @permissions = Permission.find(:all)
  end

  def show
    @permission = Permission.find(params[:id])
  end

  def new
    @permission = Permission.new( { :hardware_resource_group_id => params[:hardware_resource_group_id],
                                    :quota_id => params[:quota_id]})
  end

  def create
    @permission = Permission.new(params[:permission])
    if @permission.save
      flash[:notice] = 'Permission was successfully created.'
      if @permission.hardware_resource_group
        redirect_to :controller => 'pool', :action => 'show', :id => @permission.hardware_resource_group_id
      elsif @permission.quota
        redirect_to :controller => 'quota', :action => 'show', :id => @permission.quota_id
      else
        redirect_to :action => 'show', :id => @permission
      end
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
    @permission = Permission.find(params[:id])
    quota_id = @permission.quota_id
    pool_id =  @permission.permission.hardware_resource_group_id
    if @permission.destroy
      if pool_id
        redirect_to :controller => 'pool', :action => 'show', :id => pool_id
      elsif quota_id
        redirect_to :controller => 'quota', :action => 'show', :id => quota_id
      else
        redirect_to :action => 'list'
      end
    end
  end
end
