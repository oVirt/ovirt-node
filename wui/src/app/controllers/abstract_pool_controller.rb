class AbstractPoolController < ApplicationController
  # GETs should be safe (see http://www.w3.org/2001/tag/doc/whenToUseGet.html)
  verify :method => :post, :only => [ :destroy, :create, :update ],
         :redirect_to => { :action => :list }

  before_filter :pre_new, :only => [:new]
  before_filter :pre_create, :only => [:create]
  before_filter :pre_edit, :only => [:show, :edit, :update, :destroy]
  before_filter :authorize_admin, :only => [:new, :create, :edit, :update, :destroy]


  def show
    set_perms(@perm_pool)
    unless @can_monitor
      flash[:notice] = 'You do not have permission to view this hardware pool: redirecting to top level'
      redirect_to :controller => "dashboard"
    end
  end

  def new 
  end
  def edit
  end

  protected
  def authorize_admin
    set_perms(@perm_pool)
    unless @is_admin
      flash[:notice] = 'You do not have permission to create or modify a pool here '
      redirect_to :action => 'show', :id => @perm_pool
    end
    false
  end

  def move_contents_and_destroy(pool)
    pool.hosts.each do |host| 
      host.hardware_pool_id=superpool.id
      host.save
    end
    pool.storage_volumes.each do |vol| 
      vol.hardware_pool_id=superpool.id
      vol.save
    end
    # what about quotas -- for now they're deleted
    pool.destroy
  end

end
