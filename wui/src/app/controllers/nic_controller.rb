class NicController < ApplicationController
  def index
    list
    render :action => 'list'
  end

  # GETs should be safe (see http://www.w3.org/2001/tag/doc/whenToUseGet.html)
  verify :method => :post, :only => [ :destroy, :create, :update ],
         :redirect_to => { :action => :list }

  def list
    @nics = Nic.find(:all)
  end

  def show
    @nic = Nic.find(params[:id])
  end

  def new
    @nic = Nic.new({ :host_id => params[:host_id] })
  end

  def create
    @nic = Nic.new(params[:nic])
    if @nic.save
      host_url = url_for( :controller => "host", :action => "show", :id => @nic.host )
      nic_url = url_for( :controller => "nic", :action => "show", :id => @nic )
      flash[:notice] = 'Nic <a class="show" href="%s">%s</a> has been added to <a class="show" href="%s">%s</a>.' % [ nic_url, @nic.mac, host_url, @nic.host.hostname ]
      redirect_to :controller => 'host', :action => 'show', :id => @nic.host_id
    else
      render :action => 'new'
    end
  end

  def edit
    @nic = Nic.find(params[:id])
  end

  def update
    @nic = Nic.find(params[:id])
    if @nic.update_attributes(params[:nic])
      host_url = url_for( :controller => "host", :action => "show", :id => @nic.host )
      nic_url = url_for( :controller => "nic", :action => "show", :id => @nic )
      flash[:notice] = 'Nic <a class="show" href="%s">%s</a> has been updated for <a class="show" href="%s">%s</a>.' % [ nic_url, @nic.mac, host_url, @nic.host.hostname ]
      redirect_to :controller => 'host', :action => 'show', :id => @nic.host_id
    else
      render :action => 'edit'
    end
  end

  def destroy
    @nic = Nic.find(params[:id])
    hostname = @nic.host.hostname
    mac = @nic.mac
    host_url = url_for( :controller => "host", :action => "show", :id => @nic.host )
    host_id = @nic.host_id
    @nic.destroy
    flash[:notice] = 'Nic %s has been removed from <a class="show" href="%s">%s</a>.' % [ mac, host_url, hostname ]
    redirect_to :controller => 'host', :action => 'show', :id => host_id
  end
end
