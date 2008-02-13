# Filters added to this controller apply to all controllers in the application.
# Likewise, all the methods added will be available for all controllers.

class ApplicationController < ActionController::Base
  # Pick a unique cookie name to distinguish our session data from others'
  session :session_key => '_ovirt_session_id'
  init_gettext "ovirt"
  layout 'default'

  before_filter :pre_new, :only => [:new]
  before_filter :pre_create, :only => [:create]
  before_filter :pre_edit, :only => [:edit, :update, :destroy]
  before_filter :pre_show, :only => [:show]
  before_filter :authorize_admin, :only => [:new, :create, :edit, :update, :destroy]

  def get_login_user
    user_from_principal(request.env["HTTP_X_FORWARDED_USER"])
  end
  
  def user_from_principal(principal)
    principal.split('@')[0]
  end

  def set_perms(hwpool)
    @user = get_login_user
    @is_admin = hwpool.is_admin(@user)
    @can_monitor = hwpool.can_monitor(@user)
    @can_delegate = hwpool.can_delegate(@user)
  end

  protected
  # permissions checking

  def pre_new
  end
  def pre_create
  end
  def pre_edit
  end
  def pre_show
  end

  def authorize_admin
    if @perm_obj
      set_perms(@perm_obj)
      unless @is_admin
        @redir_obj = @perm_obj unless @redir_obj
        flash[:notice] = 'You do not have permission to create or modify this item '
        if @redir_controller
          redirect_to :controller => @redir_controller, :action => 'show', :id => @redir_obj
        else
          redirect_to :action => 'show', :id => @redir_obj
        end
        false
      end
    end
  end


end
