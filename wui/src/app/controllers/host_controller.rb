class HostController < ApplicationController
  def index
    list
    render :action => 'list'
  end

  # GETs should be safe (see http://www.w3.org/2001/tag/doc/whenToUseGet.html)
  verify :method => :post, :only => [ :destroy, :create, :update ],
         :redirect_to => { :action => :list }

  def list
    @attach_to_group=params[:attach_to_group]
    if @attach_to_group
      group = HardwareResourceGroup.find(@attach_to_group)
      conditions = "hardware_resource_group_id is null"
      conditions += " or hardware_resource_group_id=#{group.supergroup_id}" if group.supergroup
      @hosts = Host.find(:all, :conditions => conditions)
    else
      @host_pages, @hosts = paginate :hosts, :per_page => 10
    end
  end

  def show
    @host = Host.find(params[:id])
  end

  def new
    @host = Host.new
  end

  def create
    @host = Host.new(params[:host])
    if @host.save
      flash[:notice] = '<a class="show" href="%s">%s</a> was created.' % [ url_for(:controller => "host", :action => "show", :id => @host), @host.hostname ]
      redirect_to :controller => 'admin', :action => 'index'
    else
      render :action => 'new'
    end
  end

  def edit
    @host = Host.find(params[:id])
  end

  def update
    @host = Host.find(params[:id])
    if @host.update_attributes(params[:host])
      flash[:notice] = '<a class="show" href="%s">%s</a> was updated.' % [ url_for(:controller => "host", :action => "show", :id => @host), @host.hostname ]
      redirect_to :action => 'show', :id => @host
    else
      render :action => 'edit'
    end
  end

  def destroy
    h = Host.find(params[:id])
    hostname = h.hostname
    h.destroy
    flash[:notice] = '%s was destroyed.' % hostname
    redirect_to :controller => 'admin', :action => 'index'
  end

  def disable
    @host = Host.find(params[:id])
    @host.is_disabled = 1
    if @host.save
      flash[:notice] = '<a class="show" href="%s">%s</a> was disabled.' % [ url_for(:controller => "host", :action => "show", :id => @host), @host.hostname ]
    else
      flash[:notice] = 'Disable failed for <a class="show" href="%s">%s</a>.' % [ url_for(:controller => "host", :action => "show", :id => @host), @host.hostname ]
    end
    redirect_to :action => 'show', :id => @host
  end

  def enable
    @host = Host.find(params[:id])
    @host.is_disabled = 0
    if @host.save
      flash[:notice] = '<a class="show" href="%s">%s</a> was enabled.' % [ url_for(:controller => "host", :action => "show", :id => @host), @host.hostname ]
    else
      flash[:notice] = 'Enable failed for <a class="show" href="%s">%s</a>.' % [ url_for(:controller => "host", :action => "show", :id => @host), @host.hostname ]
    end
    redirect_to :action => 'show', :id => @host
  end
  def attach_to_group
    @host = Host.find(params[:id])
    group = HardwareResourceGroup.find(params[:hardware_resource_group_id])
    host_url = url_for(:controller => "host", :action => "show", :id => @host)
    group_url = url_for(:controller => "hardware_resource_group", :action => "show", :id => group)
    @host.hardware_resource_group_id = group.id
    if @host.save
      flash[:notice] = '<a class="show" href="%s">%s</a> is attached to <a href="%s">%s</a>.' %  [ host_url ,@host.hostname, group_url, group.name ]
      redirect_to :controller => 'pool', :action => 'show', :id => group
    else
      flash[:notice] = 'Problem attaching <a class="show" href="%s">%s</a> to <a href="%s">%s</a>.' %  [ host_url ,@host.hostname, host_url, host.hostname ]
      redirect_to :controller => 'pool', :action => 'show', :id => group
    end
  end


end
