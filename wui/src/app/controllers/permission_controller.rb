class PermissionController < ApplicationController
  # GETs should be safe (see http://www.w3.org/2001/tag/doc/whenToUseGet.html)
  verify :method => :post, :only => [ :destroy, :create, :update ],
         :redirect_to => { :action => :list }

  def set_perms
    @user = get_login_user
    if @permission.hardware_resource_group
      @is_admin = @permission.hardware_resource_group.is_admin(@user)
      @can_monitor = @permission.hardware_resource_group.can_monitor(@user)
      @can_delegate = @permission.hardware_resource_group.can_delegate(@user)
    elsif @permission.quota
      @is_admin = @permission.quota.is_admin(@user)
      @can_monitor = @permission.quota.can_monitor(@user)
      @can_delegate = @permission.quota.can_delegate(@user)
    else
      @is_admin = false
      @can_monitor = false
      @can_delegate = false
    end
  end

  def redirect_to_parent
    if @permission.hardware_resource_group
      redirect_to :controller => 'pool', :action => 'show', :id => @permission.hardware_resource_group_id
    elsif @permission.quota
      redirect_to :controller => 'quota', :action => 'show', :id => @permission.quota_id
    else
      redirect_to :controller => 'pool', :action => 'list'
    end
  end

  def show
    @permission = Permission.find(params[:id])
    set_perms
    # admin permission required to view permissions
    unless @is_admin
      flash[:notice] = 'You do not have permission to view this permission record'
      redirect_to_parent
    end
  end

  def new
    @permission = Permission.new( { :hardware_resource_group_id => params[:hardware_resource_group_id],
                                    :quota_id => params[:quota_id]})
    set_perms
    # admin permission required to view permissions
    unless @can_delegate
      flash[:notice] = 'You do not have permission to create this permission record'
      redirect_to_parent
    end
  end

  def create
    @permission = Permission.new(params[:permission])
    set_perms
    unless @can_delegate
      flash[:notice] = 'You do not have permission to create this permission record'
      redirect_to_parent
    else
      if @permission.save
        flash[:notice] = 'Permission was successfully created.'
        redirect_to_parent
      else
        render :action => 'new'
      end
    end
  end

  def destroy
    @permission = Permission.find(params[:id])
    set_perms
    unless @can_delegate
      flash[:notice] = 'You do not have permission to delete this permission record'
      redirect_to_parent
    else
      quota_id = @permission.quota_id
      pool_id =  @permission.hardware_resource_group_id
      if @permission.destroy
        if pool_id
          redirect_to :controller => 'pool', :action => 'show', :id => pool_id
        elsif quota_id
          redirect_to :controller => 'quota', :action => 'show', :id => quota_id
        else
          redirect_to :controller => 'quota', :action => 'list'
        end
      end
    end
  end
end
