class HostController < ApplicationController
  def index
    list
    render :action => 'list'
  end

  # GETs should be safe (see http://www.w3.org/2001/tag/doc/whenToUseGet.html)
  verify :method => :post, :only => [ :destroy, :create, :update ],
         :redirect_to => { :action => :list }

  def list
    @host_pages, @hosts = paginate :hosts, :per_page => 10
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
      flash[:notice] = 'Host was successfully created.'
      redirect_to :action => 'list'
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
      flash[:notice] = 'Host was successfully updated.'
      redirect_to :action => 'show', :id => @host
    else
      render :action => 'edit'
    end
  end

  def destroy
    Host.find(params[:id]).destroy
    redirect_to :action => 'list'
  end
end
