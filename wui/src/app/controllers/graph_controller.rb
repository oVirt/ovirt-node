require 'util/stats/Stats'

class GraphController < ApplicationController
  layout nil

  # generate layout for avaialability bar graphs
  def availability_graph
    @id = params[:id]
    @target = params[:target]

    if @target == 'cpu'
        pool = HardwarePool.find(@id)
        @label = "CPUs"
        @graph_data = { 'Available' => 0, 'Used' => 0, 'Total' => pool.total_resources[:cpus] }
        pool.all_sub_hardware_pools.each{ |subpool|
            @graph_data['Total'] += subpool.total_resources[:cpus]
        }
        pool.all_sub_vm_resource_pools.each{ |subpool|
            @graph_data['Used']  += subpool.allocated_resources[:current][:cpus]
        }
       @graph_data['Available'] = (@graph_data['Total'] - @graph_data['Used'])
    elsif @target == 'vcpu'
        pool = VmResourcePool.find(@id)
        @label = "VCPUs"
        @graph_data = { 'Available' => 0, 'Used' => pool.allocated_resources[:current][:cpus], 'Total' => pool.total_resources[:cpus] }
        pool.all_sub_vm_resource_pools.each{ |subpool|
            @graph_data['Total'] += subpool.total_resources[:cpus]
            @graph_data['Used']  += subpool.allocated_resources[:current][:cpus]
        }
       @graph_data['Available'] = (@graph_data['Total'] - @graph_data['Used'])
    elsif @target == 'memory'
        pool = HardwarePool.find(@id)
        @label = "GB of Memory"
        @graph_data = { 'Available' => 0, 'Used' => 0, 'Total' => pool.total_resources[:memory] }
        pool.all_sub_hardware_pools.each{ |subpool|
            @graph_data['Total'] += subpool.total_resources[:memory]
        }
        pool.all_sub_vm_resource_pools.each{ |subpool|
            @graph_data['Used']  += subpool.allocated_resources[:current][:memory]
        }
        @graph_data['Available'] = (@graph_data['Total'] - @graph_data['Used'])
    elsif @target == 'vram'
        pool = VmResourcePool.find(@id)
        @label = "GB of VMemory"
        @graph_data = { 'Available' => 0, 'Used' => pool.allocated_resources[:current][:memory], 'Total' => pool.total_resources[:memory] }
        pool.all_sub_vm_resource_pools.each{ |subpool|
            @graph_data['Total'] += subpool.total_resources[:memory]
            @graph_data['Used']  += subpool.allocated_resources[:current][:memory]
        }
       @graph_data['Available'] = (@graph_data['Total'] - @graph_data['Used'])
    elsif @target == 'vms'
        @label = "Virtual Machines"
        @graph_data = { 'Available' => 5, 'Used' => 15, 'Total' => 20 }
        # TODO
    elsif @target == 'vm_quotas'
        @label = 'Virtual Machines'
        @graph_data = { 'Available' => 5, 'Used' => 10, 'Total' => 15 }
        # TODO
    end
  end

  # retrieves data to be used by availablilty bar graphs
  def availability_graph_data
    target = params[:target]
    @graph_data = { 'Available' => params[:available].to_i, 'Used' => params[:used].to_i, 'Total' => params[:total].to_i }


    color = 'blue'
    data_sets = []
    if (@graph_data['Total'] > @graph_data['Used'])
        # 3/4 is the critical boundry for now
        color = 'red' if (@graph_data['Used'].to_f / @graph_data['Total'].to_f) > 0.75 
        data_sets.push ({ :name => target + '_used', :values => [@graph_data['Used']],
                          :fill => color, :stroke => 'lightgray', :strokeWidth => 1 },
                        { :name => target + '_available', 
                          :values => [@graph_data['Available']], :fill => 'white',
                          :stroke => 'lightgray', :strokeWidth => 1})
    else
        data_sets.push ({ :name => target + '_available', :values => [@graph_data['Available']],
                          :fill => 'white', :stroke => 'lightgray', :strokeWidth => 1 },
                        { :name => target + '_used', 
                          :values => [@graph_data['Used']], :fill => 'red',
                          :stroke => 'lightgray', :strokeWidth => 1})
    end

    render :json => { :timepoints => [], :dataset => data_sets }
  end

  # generate layout for history graphs
  def history_graphs
    @id = params[:id]
    @peak_history = { :color => 'red',  :values => [ 100, 99, 98, 93, 95, 12, 92] }
    @avg_history  = { :color => 'blue', :values => [12, 23, 42, 33, 12, 23, 65] }
  end

  # retrieves data for history graphs
  def history_graph_data
    history_graphs
    target = params[:target]
    @pool = Pool.find(@id)
    
    today = Time.now
    #requestList = [ ]
    dates = [ Date::ABBR_MONTHNAMES[today.month] + ' ' + today.day.to_s ]
    0.upto(6){ |x|  # TODO get # of days from wui
       dte = today - x
       dates.push ( Date::ABBR_MONTHNAMES[dte.month] + ' ' + dte.day.to_s )
       #requestList.push ( StatsRequest.new (@pool.id.to_s, target, 0, "used", dte.to_i - 3600, 3600, 0), 
       #                   StatsRequest.new (@pool.id.to_s, target, 0, "peak", dte.to_i - 3600, 3600, 0) )
    }
    dates.reverse! # want in ascending order
    #requestList.reverse!

    #statsList = getStatsData?( requestList )
    #statsList.each { |stat|
    #    devClass = stat.get_devClass?
    #    counter  = stat.get_counter?
    #    stat.get_data?.each{ |data|
    #        value    = data.get_value?.to_i
    #        if devClass == target
    #            if counter == "used"
    #                @avg_history[:values].push value
    #            else
    #            #elsif counter == "peak"
    #                @peak_history[:values].push value
    #            end
    #        end
    #    }
    #}

    graph_object = {
       :timepoints => dates,
       :dataset => 
        [
            {
                :name => target + "peak",
                :values => @peak_history[:values],
                :stroke => @peak_history[:color],
                :strokeWidth => 1
            },
            {
                :name => target + "average",
                :values => @avg_history[:values], 
                :stroke => @avg_history[:color],
                :strokeWidth => 1
            }
       ]
    }
    render :json => graph_object
  end


  # generate data for load graphs
  def load_graph_data
    @id     = params[:id]
    target = params[:target]

    # TODO get load from  id/target
    # 'host' / 'resource' / 'vm'
    load_value = rand(10)
    load_remaining = 10 - load_value
    
    graph_object = {
       :timepoints => [],
       :dataset => 
        [
            {
                :name => target,
                :values => [load_value],
                :fill => 'blue',
                :stroke => 'lightgray',
                :strokeWidth => 1
            },
            {
                :name => target + "remaining",
                :values => [load_remaining],
                :fill => 'white',
                :stroke => 'lightgray',
                :strokeWidth => 1
            }
       ]
    }
    render :json => graph_object

  end
  
  # generate layout for snapshot graphs
  def snapshot_graph
    @id = params[:id]
    @target = params[:target]

    #ret_time = Time.now.to_i
    #@snapshots = { :avg  => { :overall_load => 0, :cpu => 0, :in => 0, :out => 0, :io => 0 },
    #               :peak => { :overall_load => 0, :cpu => 0, :in => 0, :out => 0, :io => 0 }}
    #requestList = []
    #requestList << StatsRequest.new(@id.to_s, "system", 0, "used", ret_time, 3600, 0)
    #requestList << StatsRequest.new(@id.to_s, "system", 0, "peak", ret_time, 3600, 0)
    #requestList << StatsRequest.new(@id.to_s, "cpu",    0, "used", ret_time, 3600, 0)
    #requestList << StatsRequest.new(@id.to_s, "cpu",    0, "peak", ret_time, 3600, 0)
    #requestList << StatsRequest.new(@id.to_s, "in",     0, "used", ret_time, 3600, 0)
    #requestList << StatsRequest.new(@id.to_s, "in",     0, "peak", ret_time, 3600, 0)
    #requestList << StatsRequest.new(@id.to_s, "out",    0, "used", ret_time, 3600, 0)
    #requestList << StatsRequest.new(@id.to_s, "out",    0, "peak", ret_time, 3600, 0)
    #requestList << StatsRequest.new(@id.to_s, "io",     0, "used", ret_time, 3600, 0)
    #requestList << StatsRequest.new(@id.to_s, "io",     0, "peak", ret_time, 3600, 0)
    #statsList = getStatsData?( requestList )
    #statsList.each { |stat|
    #    devClass = stat.get_devClass?
    #    counter  = stat.get_counter?
    #    stat.get_data?.each{ |data|
    #        value = data.get_value?.to_i
    #        if counter == "used"
    #            if devClass == "system"
    #                @snapshots[:avg][:overall_load] = value
    #            elsif devClass == "cpu"
    #                @snapshots[:avg][:cpu] = value
    #            elsif devClass == "in"
    #                @snapshots[:avg][:in]  = value
    #            elsif devClass == "out"
    #                @snapshots[:avg][:out] = value
    #            elsif devClass == "io"
    #                @snapshots[:avg][:io]  = value
    #            end
    #        else
    #        #elsif counter == "peak"
    #            if devClass == "system"
    #                @snapshots[:peak][:overall_load] = value.to_i
    #            elsif devClass == "cpu"
    #                @snapshots[:peak][:cpu] = value.to_i
    #            elsif devClass == "in"
    #                @snapshots[:peak][:in]  = value.to_i
    #            elsif devClass == "out"
    #                @snapshots[:peak][:out] = value.to_i
    #            elsif devClass == "io"
    #                @snapshots[:peak][:io]  = value.to_i
    #            end
    #        end
    #    }
    #}
    @snapshots = { :avg  => { :overall_load => 500, :cpu => 10, :in => 100, :out => 1024, :io => 200 },
                   :peak => { :overall_load => 100, :cpu => 50, :in => 12, :out => 72, :io => 100 } }
    
  end

  # retrieves data used by snapshot graphs
  def snapshot_graph_data
    snapshot_graph

    target =  params[:target]
    snapshot = nil
    if target == 'overall_load'
        snapshot = @snapshots[:avg][:overall_load]
    elsif target == 'cpu'
        snapshot = @snapshots[:avg][:cpu]
    elsif target == 'in'
        snapshot = @snapshots[:avg][:in]
    elsif target == 'out'
        snapshot = @snapshots[:avg][:out]
    elsif target == 'io'
        snapshot = @snapshots[:avg][:io]
    end

    snapshot_remaining = 1024 - snapshot

    color = 'blue'
    color = 'red' if (snapshot.to_f / 1024.to_f) > 0.75  # 3/4 is the critical boundry for now

    graph_object = {
       :timepoints => [],
       :dataset => 
        [
            {
                :name => target,
                :values => [snapshot],
                :fill => color,
                :stroke => 'lightgray',
                :strokeWidth => 1
            },
            {
                :name => target + "remaining",
                :values => [snapshot_remaining],
                :fill => 'white',
                :stroke => 'lightgray',
                :strokeWidth => 1
            }
       ]
    }
    render :json => graph_object
  end

  #This is static test data to show how we would format whatever we get back from the 
  #data api.  We can pass that api:
  #*  node id
  #*  type of data we want back (things like summary, memory, storage, etc.)
  #*  timeframe we are interested in.  This one goes into 'timepoints'
  #   and probably would call some rails helpers to format the date info however we want

  def graph
    if params[:type] =="Memory" 
       graph_object = {
        :timepoints => [],
        :dataset => [{
            :name =>'IE', 
            :values => [86.64], 
            :fill => 'lightblue', 
            :stroke => 'blue', 
            :strokeWidth => 3
          }
        ]
      } 
    elsif params[:type] == "detail"
      graph_object = {
        :timepoints => ["April 1", "April 2","April 3","April 4","April 5","April 6","April 7"],
        :dataset => [{
            :name =>'Peak', 
            :values => [75.97, 71.80, 68.16, 56.64,95.97, 81.80, 28.16], 
            :fill => 'lightblue', 
            :stroke => 'blue', 
            :strokeWidth => 3
          }]
      }
    else      
      graph_object = {
        :timepoints => ["April 1", "April 2","April 3","April 4"],
        :dataset => [{
            :name =>'Peak', 
            :values => [95.97, 91.80, 88.16, 86.64], 
            :fill => 'lightblue', 
            :stroke => 'blue', 
            :strokeWidth => 3
          },
          {
            :name =>'Average', 
            :values => [3.39, 2.83, 1.61, 0.00], 
            :fill => 'pink', 
            :stroke => 'red', 
            :strokeWidth => 3
          }
        ]
      }
    end
    render :json => graph_object
  end
end
