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
    @user_id=params[:user_id]
  end

  def create
    params[:vm]["num_vcpus_used"] = params[:vm]["num_vcpus_allocated"] unless params[:vm]["num_vcpus_used"]
    params[:vm]["memory_used"] = params[:vm]["memory_allocated"] unless params[:vm]["memory_used"]
    @vm = Vm.new(params[:vm])
    if @vm.save
      flash[:notice] = 'Vm was successfully created.'
      redirect_to :controller => 'quota', :action => 'show', :id => @vm.user.user_quota
    else
      render :action => 'new'
    end
  end

  def edit
    @vm = Vm.find(params[:id])
    @user_id=@vm.user_id
  end

  def update
    @vm = Vm.find(params[:id])
    params[:vm]["num_vcpus_used"] = params[:vm]["num_vcpus_allocated"] unless params[:vm]["num_vcpus_used"]
    params[:vm]["memory_used"] = params[:vm]["memory_allocated"] unless params[:vm]["memory_used"]
    if @vm.update_attributes(params[:vm])
      flash[:notice] = 'Vm was successfully updated.'
      redirect_to :controller => 'quota', :action => 'show', :id => @vm.user.user_quota
    else
      render :action => 'edit'
    end
  end

  def destroy
    @vm = Vm.find(params[:id])
    quota = @vm.user.user_quota
    @vm.destroy
    redirect_to :controller => 'quota', :action => 'show', :id => quota
  end
end
