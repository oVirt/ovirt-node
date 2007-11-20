class NicController < ApplicationController
  def index
    list
    render :action => 'list'
  end

  # GETs should be safe (see http://www.w3.org/2001/tag/doc/whenToUseGet.html)
  verify :method => :post, :only => [ :destroy, :create, :update ],
         :redirect_to => { :action => :list }

  def list
    @nic_pages, @nics = paginate :nics, :per_page => 10
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
      flash[:notice] = 'Nic was successfully added.'
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
      flash[:notice] = 'Nic was successfully updated.'
      redirect_to :controller => 'host', :action => 'show', :id => @nic.host_id
    else
      render :action => 'edit'
    end
  end

  def destroy
    @nic = Nic.find(params[:id])
    host_id = @nic.host_id
    @nic.destroy
    redirect_to :controller => 'host', :action => 'show', :id => host_id
  end
end
