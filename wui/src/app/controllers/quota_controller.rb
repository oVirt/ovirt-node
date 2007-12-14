class QuotaController < ApplicationController
  def index
    list
    render :action => 'list'
  end

  # GETs should be safe (see http://www.w3.org/2001/tag/doc/whenToUseGet.html)
  verify :method => :post, :only => [ :destroy, :create, :update ],
         :redirect_to => { :action => :list }

  def list
    @quota_pages, @quotas = paginate :quotas, :per_page => 10
  end

  def show
    @quota = Quota.find(params[:id])
  end

  def new
    @quota = Quota.new( { :user_id => params[:user_id] } )
  end

  def create
    @quota = Quota.new(params[:quota])
    if @quota.save
      flash[:notice] = 'Quota was successfully created.'
      redirect_to :action => 'list'
    else
      render :action => 'new'
    end
  end

  def edit
    @quota = Quota.find(params[:id])
  end

  def update
    @quota = Quota.find(params[:id])
    if @quota.update_attributes(params[:quota])
      flash[:notice] = 'Quota was successfully updated.'
      redirect_to :action => 'show', :id => @quota
    else
      render :action => 'edit'
    end
  end

  def destroy
    @quota = Quota.find(params[:id])
    user_id = @quota.user_id
    @quota.destroy
    redirect_to :controller => 'user', :action => 'show', :id => user_id
  end
end
