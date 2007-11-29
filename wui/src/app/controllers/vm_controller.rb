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
    # random MAC
    mac = [ 0x00, 0x16, 0x3e, rand(0x7f), rand(0xff), rand(0xff) ]
    # random uuid
    uuid = ["%02x" * 4, "%02x" * 2, "%02x" * 2, "%02x" * 2, "%02x" * 6].join("-") % 
      Array.new(16) {|x| rand(0xff) }
    newargs = { 
      :user_id => params[:user_id],
      :vnic_mac_addr => mac.collect {|x| "%02x" % x}.join(":"),
      :uuid => uuid
    }

    @vm = Vm.new( newargs )
  end

  def create
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
  end

  def update
    @vm = Vm.find(params[:id])
    #needs restart if certain fields are changed (since those will only take effect the next startup)
    needs_restart = false
    Vm::NEEDS_RESTART_FIELDS.each do |field|
      unless @vm[field].to_s == params[:vm][field]
        needs_restart = true
        break
      end
    end
    params[:vm][:needs_restart] = 1 if needs_restart
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
