class StorageController < ApplicationController
  def index
    list
    render :action => 'list'
  end

  # GETs should be safe (see http://www.w3.org/2001/tag/doc/whenToUseGet.html)
  verify :method => :post, :only => [ :destroy, :create, :update ],
         :redirect_to => { :action => :list }

  def list
    @storage_volume_pages, @storage_volumes = paginate :storage_volumes, :per_page => 10
    @attach_to_host=params[:attach_to_host]
    @attach_to_vm=params[:attach_to_vm]

  end

  def show
    @storage_volume = StorageVolume.find(params[:id])
  end

  def new
    @storage_volume = StorageVolume.new
  end

  def create
    @storage_volume = StorageVolume.new(params[:storage_volume])
    if @storage_volume.save
      storage_url = url_for(:controller => "storage", :action => "show", :id => @storage_volume)
      flash[:notice] = '<a class="show" href="%s">%s</a> was successfully created.' % [ storage_url ,@storage_volume.ip_addr]
      redirect_to :controller => 'admin', :action => 'index'
    else
      render :action => 'new'
    end
  end

  def edit
    @storage_volume = StorageVolume.find(params[:id])
  end

  def update
    @storage_volume = StorageVolume.find(params[:id])
    if @storage_volume.update_attributes(params[:storage_volume])
      storage_url = url_for(:controller => "storage", :action => "show", :id => @storage_volume)
      flash[:notice] = '<a class="show" href="%s">%s</a> was successfully updated.' % [ storage_url ,@storage_volume.ip_addr]
      redirect_to :action => 'show', :id => @storage_volume
    else
      render :action => 'edit'
    end
  end

  def destroy
    StorageVolume.find(params[:id]).destroy
    redirect_to :controller => 'admin', :action => 'index'
  end

  def attach_to_host
    @storage_volume = StorageVolume.find(params[:id])
    host = Host.find(params[:host_id])
    storage_url = url_for(:controller => "storage", :action => "show", :id => @storage_volume)
    host_url = url_for(:controller => "host", :action => "show", :id => host)
    if @storage_volume.hosts.include?(host)
      flash[:notice] = '<a class="show" href="%s">%s</a> is already attached to <a href="%s">%s</a>.' % [ storage_url ,@storage_volume.ip_addr, host_url , host.hostname]
      redirect_to :controller => 'host', :action => 'show', :id => host
    elsif @storage_volume.hosts << host 
      flash[:notice] = '<a class="show" href="%s">%s</a> is attached to <a href="%s">%s</a>.' %  [ storage_url ,@storage_volume.ip_addr, host_url, host.hostname ]
      redirect_to :controller => 'host', :action => 'show', :id => host
    else
      flash[:notice] = 'Problem attaching <a class="show" href="%s">%s</a> to <a href="%s">%s</a>.' %  [ storage_url ,@storage_volume.ip_addr, host_url, host.hostname ]
      redirect_to :controller => 'host', :action => 'show', :id => host
    end
  end

  def remove_from_host
    @storage_volume = StorageVolume.find(params[:id])
    host = Host.find(params[:host_id])
    storage_url = url_for(:controller => "storage", :action => "show", :id => @storage_volume)
    host_url = url_for(:controller => "host", :action => "show", :id => host)
    if @storage_volume.hosts.include?(host)
      if @storage_volume.hosts.delete(host)
        flash[:notice] = '<a class="show" href="%s">%s</a> is removed from <a href="%s">%s</a>.' %[ storage_url ,@storage_volume.ip_addr, host_url, host.hostname ]
        redirect_to :controller => 'host', :action => 'show', :id => host
      else
        flash[:notice] = 'Problem attaching <a class="show" href="%s">%s</a> to <a href="%s">%s</a>.' % [ storage_url ,@storage_volume.ip_addr, host_url, host.hostname ]
        redirect_to :controller => 'host', :action => 'show', :id => host
      end
    else
      flash[:notice] = '<a class="show" href="%s">%s</a> is not attached to <a href="%s">%s</a>.' % [ storage_url ,@storage_volume.ip_addr, host_url, host.hostname ]
      redirect_to :controller => 'host', :action => 'show', :id => host
    end
  end

end
