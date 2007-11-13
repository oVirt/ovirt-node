class QuotaController < ApplicationController
  def index
    list
    render :action => 'list'
  end

  # GETs should be safe (see http://www.w3.org/2001/tag/doc/whenToUseGet.html)
  verify :method => :post, :only => [ :destroy, :create, :update ],
         :redirect_to => { :action => :list }

  def list
    @user_quota_pages, @user_quotas = paginate :user_quotas, :per_page => 10
  end

  def show
    @user_quota = UserQuota.find(params[:id])
  end

  def new
    @user_quota = UserQuota.new
  end

  def create
    @user_quota = UserQuota.new(params[:user_quota])
    if @user_quota.save
      flash[:notice] = 'UserQuota was successfully created.'
      redirect_to :action => 'list'
    else
      render :action => 'new'
    end
  end

  def edit
    @user_quota = UserQuota.find(params[:id])
  end

  def update
    @user_quota = UserQuota.find(params[:id])
    if @user_quota.update_attributes(params[:user_quota])
      flash[:notice] = 'UserQuota was successfully updated.'
      redirect_to :action => 'show', :id => @user_quota
    else
      render :action => 'edit'
    end
  end

  def destroy
    UserQuota.find(params[:id]).destroy
    redirect_to :action => 'list'
  end
end
