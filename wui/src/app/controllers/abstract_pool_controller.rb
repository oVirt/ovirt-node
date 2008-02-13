class AbstractPoolController < ApplicationController
  # GETs should be safe (see http://www.w3.org/2001/tag/doc/whenToUseGet.html)
  verify :method => :post, :only => [ :destroy, :create, :update ],
         :redirect_to => { :action => :list }

  def show
    set_perms(@perm_obj)
    unless @can_monitor
      flash[:notice] = 'You do not have permission to view this hardware pool: redirecting to top level'
      redirect_to :controller => "dashboard"
    end
  end

  def new 
  end
  def edit
  end

end
