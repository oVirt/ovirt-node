class VmController < ApplicationController
  def index
    list
    render :action => 'list'
  end

  # GETs should be safe (see http://www.w3.org/2001/tag/doc/whenToUseGet.html)
  verify :method => :post, :only => [ :destroy, :create, :update ],
         :redirect_to => { :action => :list }

  def list
    @vm_pages, @vms = paginate :vms, :per_page => 10
  end

  def show
    @vm = Vm.find(params[:id])
  end

  def new
    @vm = Vm.new
  end

  def create
    @vm = Vm.new(params[:vm])
    if @vm.save
      flash[:notice] = 'Vm was successfully created.'
      redirect_to :action => 'list'
    else
      render :action => 'new'
    end
  end

  def edit
    @vm = Vm.find(params[:id])
  end

  def update
    @vm = Vm.find(params[:id])
    if @vm.update_attributes(params[:vm])
      flash[:notice] = 'Vm was successfully updated.'
      redirect_to :action => 'show', :id => @vm
    else
      render :action => 'edit'
    end
  end

  def destroy
    Vm.find(params[:id]).destroy
    redirect_to :action => 'list'
  end
end
