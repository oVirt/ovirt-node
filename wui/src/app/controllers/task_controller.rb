class TaskController < ApplicationController
  # GETs should be safe (see http://www.w3.org/2001/tag/doc/whenToUseGet.html)
  verify :method => :post, :only => [ :destroy, :create, :update ],
         :redirect_to => { :action => :list }

  def show
    @task = Task.find(params[:id])
    set_perms(@task.vm.vm_library)
    unless @can_monitor
      flash[:notice] = 'You do not have permission to view this task: redirecting to top level'
      redirect_to :controller => 'library', :action => 'list'
    end

  end

  def set_perms(perm_obj)
    @user = get_login_user
    @is_admin = perm_obj.is_admin(@user)
    @can_monitor = perm_obj.can_monitor(@user)
    @can_delegate = perm_obj.can_delegate(@user)
  end

end
