class PermissionController < ApplicationController
  # GETs should be safe (see http://www.w3.org/2001/tag/doc/whenToUseGet.html)
  verify :method => :post, :only => [ :destroy, :create, :update ],
         :redirect_to => { :action => :list }

  def set_perms
    @user = get_login_user
    if @permission.hardware_pool
      @is_admin = @permission.hardware_pool.is_admin(@user)
      @can_monitor = @permission.hardware_pool.can_monitor(@user)
      @can_delegate = @permission.hardware_pool.can_delegate(@user)
    elsif @permission.vm_library
      @is_admin = @permission.vm_library.is_admin(@user)
      @can_monitor = @permission.vm_library.can_monitor(@user)
      @can_delegate = @permission.vm_library.can_delegate(@user)
    else
      @is_admin = false
      @can_monitor = false
      @can_delegate = false
    end
  end

  def redirect_to_parent
    if @permission.hardware_pool
      redirect_to :controller => 'pool', :action => 'show', :id => @permission.hardware_pool_id
    elsif @permission.vm_library
      redirect_to :controller => 'library', :action => 'show', :id => @permission.vm_library_id
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
    @permission = Permission.new( { :hardware_pool_id => params[:hardware_pool_id],
                                    :vm_library_id => params[:vm_library_id]})
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
      vm_library_id = @permission.vm_library_id
      pool_id =  @permission.hardware_pool_id
      if @permission.destroy
        if pool_id
          redirect_to :controller => 'pool', :action => 'show', :id => pool_id
        elsif vm_library_id
          redirect_to :controller => 'library', :action => 'show', :id => vm_library_id
        else
          redirect_to :controller => 'library', :action => 'list'
        end
      end
    end
  end
end
