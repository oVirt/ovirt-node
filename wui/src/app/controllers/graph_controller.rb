require 'util/stats/Stats'

class GraphController < ApplicationController
  layout nil

  # generate layout for avaialability bar graphs
  def availability_graph
    @id = params[:id]
    @target = params[:target]

    # TODO: make this configurable
    aggregate_subpools = false
    if ['cpu', 'memory'].include? (@target)
      pool = HardwarePool.find(@id, :include => :hosts)
      if (aggregate_subpools)
        pools = pool.full_set({:include => :hosts, :conditions => "type='HardwarePool'"})
        vmpools = pool.full_set({:include => :vms, :conditions => "type='VmResourcePool'"})
      else
        pools = [pool]
        vmpools = pool.children({:include => :vms, :conditions => "type='VmResourcePool'"})
      end
      if @target == 'cpu'
        @label = "CPUs"
        used= vmpools.inject(0){ |sum, pool| sum+pool.allocated_resources[:current][:cpus] }
        total= pools.inject(0){ |sum, pool| sum+pool.hosts.total_cpus }
      elsif @target == 'memory'
        @label = "MB of Memory"
        used= vmpools.inject(0){ |sum, pool| sum+pool.allocated_resources[:current][:memory] }
        total= pools.inject(0){ |sum, pool| sum+pool.hosts.total_memory }
      end
    elsif ['vcpu', 'vram'].include? (@target)
      pool = VmResourcePool.find(@id)
      pools = aggregate_subpools ? pool.full_set({:include => :hosts}) : [pool]
      if @target == 'vcpu'
        @label = "VCPUs"
        resource_key = :cpus
      elsif @target == 'vram'
        @label = "MB of VMemory"
        resource_key = :memory
      end
      unlimited = false
      total=0
      used= pools.inject(0) { |sum, pool| sum+pool.allocated_resources[:current][resource_key] }
      pools.each do |pool| 
        resource = pool.total_resources[resource_key]
        if resource
          total +=resource
        else
          unlimited = true
        end
      end
      total = 0 if unlimited
    elsif @target == 'vms'
      @label = "Virtual Machines"
      used = 15
      total = 20
      # TODO
    elsif @target == 'vm_quotas'
      @label = 'Virtual Machines'
      used = 10
      total = 15
      # TODO
    end
    @availability_graph_data = { 'Used' => used, 'Total' => total, 'Available' => total - used}
  end

  # generate layout for history graphs
  def history_graphs
    @id = params[:id]
    @poolType = params[:poolType]
    @peak_history = { :color => 'red',  :values => [0,0,0,0,0,0,0], :dataPoints => [0,0,0,0,0,0,0] }
    @avg_history  = { :color => 'blue', :values => [0,0,0,0,0,0,0], :dataPoints => [0,0,0,0,0,0,0] }
  end

  # retrieves data for history graphs
  def history_graph_data
    history_graphs
    target = params[:target]
    poolType = params[:poolType]
    devclass = DEV_KEY_CLASSES[target]
    avgcounter  = DEV_KEY_AVGCOUNTERS[target]
    peakcounter = nil
    @pool = Pool.find(@id)
    
    today = Time.now
    firstday = today - 6
    dates = []
    0.upto(6){ |x|  # TODO get # of days from wui
       dte = today - (x * 86400) # num of secs per day
       dates.push ( Date::ABBR_MONTHNAMES[dte.month] + ' ' + dte.day.to_s )
    }
    dates.reverse! # want in ascending order

    hosts = @pool.hosts
    # temporary workaround for vm resource history 
    # graph until we have a more reqs / long term solution
    if poolType == "vm"
        hosts = []
        @pool.vms.each { |vm|
            if !vm.host.nil?
                hosts.push vm.host
            end
        }
    end

    requestList = [ ]
    @pool.hosts.each { |host|
        if target == "cpu"
            0.upto(host.num_cpus - 1){ |x|
                requestList.push ( StatsRequest.new (host.hostname, devclass, x, avgcounter, 0, 0, RRDResolution::Long) ) #, # one weeks worth of data
                                  # StatsRequest.new (@pool.id.to_s, devclass, x, peakcounter, firstday.to_i - 3600, 604800, 3600))
            }
        else
            requestList.push ( StatsRequest.new (host.hostname, devclass, 0, avgcounter, 0, 0, RRDResolution::Long) ) #, 
                           # StatsRequest.new (@pool.id.to_s, devclass, 0, peakcounter, firstday.to_i - 3600, 604800, 3600))
        end
    }

    statsList = getStatsData?( requestList )
    statsList.each { |stat|
        counter  = stat.get_counter?
        if stat.get_status? == StatsStatus::SUCCESS
            stat.get_data?.each{ |data|
                timestamp = data.get_timestamp?
                valueindex = ((timestamp.to_i - firstday.to_i) / 86400).to_i  # 86400 secs per day
                value    = data.get_value?
                if !value.nan?
                    if counter == avgcounter
                        @avg_history[:values][valueindex] += value.to_i
                        @avg_history[:dataPoints][valueindex] += 1
                    elsif counter == peakcounter
                        @peak_history[:values][valueindex] += value.to_i
                        @peak_history[:dataPoints][valueindex] += 1
                    end
                end
            }
        end
    }

    # avgerage out history for each day
    0.upto(@avg_history[:values].size - 1){ |x|
        (@avg_history[:values][x] /= @avg_history[:dataPoints][x]) if (@avg_history[:dataPoints][x] != 0)
    }
    0.upto(@peak_history[:values].size - 1){ |x|
        (@peak_history[:values][x] /= @peak_history[:dataPoints][x]) if (@peak_history[:dataPoints][x] != 0)
    }

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
    @poolType = params[:poolType]

    @snapshots = { :avg  => { 'load' => 0, 'cpu' => 0, 'netin' => 0, 'netout' => 0, 'memory' => 0 },
                   :peak => { 'load' => 0, 'cpu' => 0, 'netin' => 0, 'netout' => 0, 'memory' => 0 }}

    requestList = []
    if @target == 'host'
        requestList += _create_host_snapshot_requests(Host.find(@id).hostname)
    elsif @poolType == 'vm'
        Pool.find(@id).vms.each{ |vm|
            if !vm.host.nil?
                requestList += _create_host_snapshot_requests(vm.host.hostname)
            end
        }
    else
        Pool.find(@id).hosts.each{ |host|
            requestList += _create_host_snapshot_requests(host.hostname)
        }
    end
    
    statsList = getStatsData?( requestList )
    statsList.each { |stat|
        devClass = stat.get_devClass?
        counter  = stat.get_counter?
        if stat.get_status? == StatsStatus::SUCCESS
            stat.get_data?.each{ |data|
                value = data.get_value?
                if !value.nan?
                    if devClass == DEV_KEY_CLASSES["load"]
                        if counter == DEV_KEY_AVGCOUNTERS["load"]
                            @snapshots[:avg]["load"] = value.to_i
                        elsif counter == DEV_KEY_PEAKCOUNTERS["load"]
                            @snapshots[:peak]["load"] = value.to_i
                        end
                    elsif devClass == DEV_KEY_CLASSES["cpu"]
                        if counter == DEV_KEY_AVGCOUNTERS["cpu"]
                            @snapshots[:avg]["cpu"] = value.to_i
                        elsif counter == DEV_KEY_PEAKCOUNTERS["cpu"]
                            @snapshots[:peak]["cpu"] = value.to_i
                        end
                    elsif devClass == DEV_KEY_CLASSES["netin"]
                        if counter == DEV_KEY_AVGCOUNTERS["netin"]
                            @snapshots[:avg]["netin"] = value.to_i
                        elsif counter == DEV_KEY_PEAKCOUNTERS["netin"]
                            @snapshots[:peak]["netin"] = value.to_i
                        end
                    elsif devClass == DEV_KEY_CLASSES["netout"]
                        if counter == DEV_KEY_AVGCOUNTERS["netout"]
                            @snapshots[:avg]["netout"] = value.to_i
                        elsif counter == DEV_KEY_PEAKCOUNTERS["netout"]
                            @snapshots[:peak]["netout"] = value.to_i
                        end
                    #elsif devClass == DEV_KEY_AVGCOUNTERS["io"]
                    #    if counter == DEV_KEY_AVGCOUNTERS["io"]
                    #        @snapshots[:peak]["io"] = value.to_i
                    #    elsif counter == _dev_key_peak_counters["io"]
                    #        @snapshots[:peak]["io"] = value.to_i
                    #    end
                    end
                end
            }
        end
    }
    #@snapshots = { :avg  => { :overall_load => 500, :cpu => 10, :in => 100, :out => 1024, :io => 200 },
    #               :peak => { :overall_load => 100, :cpu => 50, :in => 12, :out => 72, :io => 100 } }
    
  end

  private

      DEV_KEY_CLASSES  = { 'cpu' => DevClass::CPU, 'memory' => DevClass::Memory, 'disk' => DevClass::Disk, 'load' => DevClass::Load, 'netin' => DevClass::NIC, 'netout' => DevClass::NIC }
      DEV_CLASS_KEYS   = DEV_KEY_CLASSES.invert

      # TODO this needs fixing / completing (cpu: more than user time? disk: ?, load: correct?, nics: correct?)
      DEV_KEY_AVGCOUNTERS = { 'cpu' => CpuCounter::User, 'memory' => MemCounter::Used, 'disk' => DiskCounter::Ops_read, 'load' => LoadCounter::Load_1min, 'netin' => NicCounter::Packets_Rx, 'netout' => NicCounter::Packets_Tx }
      DEV_AVGCOUNTER_KEYS = DEV_KEY_AVGCOUNTERS.invert

      # TODO 
      DEV_KEY_PEAKCOUNTERS = { 'cpu' => nil, 'memory' => nil, 'disk' => nil, 'load' => nil, 'netin' => nil, 'netout' => nil }
      DEV_PEAKCOUNTER_KEYS = DEV_KEY_PEAKCOUNTERS.invert

      def _create_host_snapshot_requests(hostname)
        requestList = []
        requestList << StatsRequest.new(hostname, DEV_KEY_CLASSES['load'], 0, DEV_KEY_AVGCOUNTERS['load'], 0, 0, RRDResolution::Default) # RRDResolution::Long ?
        #requestList << StatsRequest.new(hostname, "system", 0, "peak", ret_time, 3600, 0)
        requestList << StatsRequest.new(hostname, DEV_KEY_CLASSES['cpu'],  0, DEV_KEY_AVGCOUNTERS['cpu'], 0, 0, RRDResolution::Default)  # TODO instance
        #requestList << StatsRequest.new(hostname, "cpu",    0, "peak", ret_time, 3600, 0)
        #requestList << StatsRequest.new(hostname, DEV_KEY_CLASSES['netin'],0, DEV_KEY_AVGCOUNTERS['netin'], 0, 0, RRDResolution::Default) 
        #requestList << StatsRequest.new(hostname, "in",     0, "peak", ret_time, 3600, 0)
        #requestList << StatsRequest.new(hostname, DEV_KEY_CLASSES['netout'],0, DEV_KEY_AVGCOUNTERS['netout'], 0, 0, RRDResolution::Default) 
        #requestList << StatsRequest.new(hostname, "out",    0, "peak", ret_time, 3600, 0)
        #requestList << StatsRequest.new(hostname, DEV_KEY_CLASSES["io"],0, DEV_KEY_AVGCOUNTERS["io"], 0, 0, RRDResolution::Default) 
        #requestList << StatsRequest.new(hostname, "io",     0, "peak", ret_time, 3600, 0)
        return requestList
      end

end
