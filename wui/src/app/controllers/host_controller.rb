class HostController < ApplicationController
  def index
    list
    render :action => 'list'
  end

  # GETs should be safe (see http://www.w3.org/2001/tag/doc/whenToUseGet.html)
  verify :method => :post, :only => [ :destroy, :create, :update ],
         :redirect_to => { :action => :list }

  def set_perms(hwpool)
    @user = get_login_user
    @is_admin = hwpool.is_admin(@user)
    @can_monitor = hwpool.can_monitor(@user)
    @can_delegate = hwpool.can_delegate(@user)
  end

  def list
    @attach_to_pool=params[:attach_to_pool]
    if @attach_to_pool
      pool = HardwarePool.find(@attach_to_pool)
      set_perms(pool)
      unless @can_monitor
        flash[:notice] = 'You do not have permission to view this host list: redirecting to top level'
        redirect_to :controller => 'pool', :action => 'list'
      else
        conditions = "hardware_pool_id is null"
        conditions += " or hardware_pool_id=#{pool.superpool_id}" if pool.superpool
        @hosts = Host.find(:all, :conditions => conditions)
      end
    else
      # no permissions here yet -- do we disable raw host list?
      @hosts = Host.find(:all)
    end
  end

  def show
    @host = Host.find(params[:id])
    set_perms(@host.hardware_pool)
    unless @can_monitor
      flash[:notice] = 'You do not have permission to view this host: redirecting to top level'
      redirect_to :controller => 'pool', :action => 'list'
    end
  end

  def edit
    @host = Host.find(params[:id])
    set_perms(@host.hardware_pool)
    unless @is_admin
      flash[:notice] = 'You do not have permission to edit this host'
      redirect_to :action => 'show', :id => @host
    end
  end

  def update
    @host = Host.find(params[:id])
    set_perms(@host.hardware_pool)
    unless @is_admin
      flash[:notice] = 'You do not have permission to edit this host'
      redirect_to :action => 'show', :id => @host
    else
      if @host.update_attributes(params[:host])
        flash[:notice] = '<a class="show" href="%s">%s</a> was updated.' % [ url_for(:controller => "host", :action => "show", :id => @host), @host.hostname ]
        redirect_to :action => 'show', :id => @host
      else
        render :action => 'edit'
      end
    end
  end

  def disable
    @host = Host.find(params[:id])
    set_perms(@host.hardware_pool)
    unless @is_admin
      flash[:notice] = 'You do not have permission to edit this host'
      redirect_to :action => 'show', :id => @host
    else
      @host.is_disabled = 1
      if @host.save
        flash[:notice] = '<a class="show" href="%s">%s</a> was disabled.' % [ url_for(:controller => "host", :action => "show", :id => @host), @host.hostname ]
      else
        flash[:notice] = 'Disable failed for <a class="show" href="%s">%s</a>.' % [ url_for(:controller => "host", :action => "show", :id => @host), @host.hostname ]
      end
      redirect_to :action => 'show', :id => @host
    end
  end

  def enable
    @host = Host.find(params[:id])
    set_perms(@host.hardware_pool)
    unless @is_admin
      flash[:notice] = 'You do not have permission to edit this host'
      redirect_to :action => 'show', :id => @host
    else
      @host.is_disabled = 0
      if @host.save
        flash[:notice] = '<a class="show" href="%s">%s</a> was enabled.' % [ url_for(:controller => "host", :action => "show", :id => @host), @host.hostname ]
      else
        flash[:notice] = 'Enable failed for <a class="show" href="%s">%s</a>.' % [ url_for(:controller => "host", :action => "show", :id => @host), @host.hostname ]
      end
      redirect_to :action => 'show', :id => @host
    end
  end

  def attach_to_pool
    @host = Host.find(params[:id])
    set_perms(@host.hardware_pool)
    unless @is_admin
      flash[:notice] = 'You do not have permission to edit this host'
      redirect_to :action => 'show', :id => @host
    else
      pool = HardwarePool.find(params[:hardware_pool_id])
      host_url = url_for(:controller => "host", :action => "show", :id => @host)
      pool_url = url_for(:controller => "hardware_pool", :action => "show", :id => pool)
      @host.hardware_pool_id = pool.id
      if @host.save
        flash[:notice] = '<a class="show" href="%s">%s</a> is attached to <a href="%s">%s</a>.' %  [ host_url ,@host.hostname, pool_url, pool.name ]
        redirect_to :controller => 'pool', :action => 'show', :id => pool
      else
        flash[:notice] = 'Problem attaching <a class="show" href="%s">%s</a> to <a href="%s">%s</a>.' %  [ host_url ,@host.hostname, host_url, host.hostname ]
        redirect_to :controller => 'pool', :action => 'show', :id => pool
      end
    end
  end


end
