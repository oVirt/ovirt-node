# 
# Copyright (C) 2008 Red Hat, Inc.
# Written by Scott Seago <sseago@redhat.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.  A copy of the GNU General Public License is
# also available at http://www.gnu.org/copyleft/gpl.html.

class SearchController < ApplicationController

  MODELS = {"HardwarePool"     => {:controller => "hardware",
                                   :show_action => "quick_summary"},
            "VmResourcePool"   => {:controller => "resources",
                                   :show_action => "quick_summary"},
            "Host"             => {:controller => "host",
                                   :show_action => "show"},
            "Vm"               => {:controller => "vm",
                                   :show_action => "show"},
            "IscsiStoragePool" => {:controller => "storage",
                                   :show_action => "show"},
            "NfsStoragePool"   => {:controller => "storage",
                                 :show_action => "show"}}

  MULTI_TYPE_MODELS = {"StoragePool" => ["IscsiStoragePool", "NfsStoragePool"]}


  def single_result
    class_and_id = params[:class_and_id].split("_")


    redirect_to :controller => MODELS[class_and_id[0]][:controller],
                :action => MODELS[class_and_id[0]][:show_action],
                :id => class_and_id[1]
  end

  def results_internal
    @terms = params[:terms]
    @model_param = params[:model]
    @model_param ||= ""

    if @model_param == ""
      @models = MODELS.keys
    else
      @models = MULTI_TYPE_MODELS[@model_param]
      @models ||= [@model_param]
    end
    @user = get_login_user

    @page = params[:page].to_i
    @page ||= 1
    @per_page = params[:rp].to_i
    @per_page ||= 20
    @offset = (@page-1)*@per_page
    @results = ActsAsXapian::Search.new(@models,
                                        @terms,
                                       :offset => @offset,
                                       :limit => @per_page,
                                       :sort_by_prefix => nil,
                                       :collapse_by_prefix => nil)
    #FIXME filter on permissions
  end

  def results
    results_internal
    @types = [["Hardware Pools", "HardwarePool"],
              ["Virtual Machine Pools", "VmResourcePool"],
              ["Hosts", "Host"],
              ["VMs", "Vm"],
              ["Storage Pools", "StoragePool", "break"],
              ["Show All", ""]]
  end

  def results_json
    results_internal


    json_hash = {}
    json_hash[:page] = @page
    json_hash[:total] = @results.matches_estimated
    json_hash[:rows] = @results.results.collect do |result|
      item_hash = {}
      item = result[:model]
      item_hash[:id] = item.class.name+"_"+item.id.to_s
      item_hash[:cell] = ["display_name", "display_class"].collect do |attr|
        if attr.is_a? Array
          value = item
          attr.each { |attr_item| value = value.send(attr_item)}
          value
        else
          item.send(attr)
        end
      end
      item_hash[:cell] << result[:percent]
      item_hash
    end
    render :json => json_hash.to_json

  end
end
