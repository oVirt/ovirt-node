require 'util/stats/Stats'

class GraphController < ApplicationController
  layout nil

  # generate layout for avaialability bar graphs
  def availability_graph
    @id = params[:id]
    @target = params[:target]

    # TODO: make this configurable
    aggregate_subpools = false
    if ['cpu', 'memory'].include?(@target)
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
        used= vmpools.inject(0){ |sum, pool| sum+pool.allocated_resources[:current][:memory_in_mb] }
        total= pools.inject(0){ |sum, pool| sum+pool.hosts.total_memory_in_mb }
      end
    elsif ['vcpu', 'vram'].include?(@target)
      pool = VmResourcePool.find(@id)
      pools = aggregate_subpools ? pool.full_set({:include => :hosts}) : [pool]
      if @target == 'vcpu'
        @label = "VCPUs"
        resource_key = :cpus
      elsif @target == 'vram'
        @label = "MB of VMemory"
        resource_key = :memory_in_mb
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
    end

    @availability_graph_data = { 'Used' => used, 'Total' => total, 'Available' => total - used}
  end

  # generate layout for history graphs
  def history_graphs
    @id = params[:id]
    @poolType = params[:poolType]
    @peak_history = { :color => 'red',  :values => [], :dataPoints => [] }
    @avg_history  = { :color => 'blue', :values => [], :dataPoints => [] }
    @roll_peak_history = { :color => 'black',  :values => [], :dataPoints => [] }
    @roll_avg_history  = { :color => 'green', :values => [], :dataPoints => [] }
  end

  # retrieves data for history graphs
  def history_graph_data
    history_graphs
    myDays = params[:days]
    target = params[:target]
    poolType = params[:poolType]
    devclass = DEV_KEY_CLASSES[target]
    counter  = DEV_KEY_COUNTERS[target]
    @pool = Pool.find(@id)
    
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

    startTime = 0
    duration, resolution = _get_snapshot_time_params(myDays.to_i)
    
    requestList = [ ]
    @pool.hosts.each { |host|
        if target == "cpu"
            0.upto(host.num_cpus - 1){ |x|
                requestList.push( StatsRequest.new(host.hostname, devclass, x, counter, startTime, duration, resolution, DataFunction::Average), 
                              StatsRequest.new(host.hostname, devclass, x, counter, startTime, duration, resolution, DataFunction::Peak),
                              StatsRequest.new(host.hostname, devclass, x, counter, startTime, duration, resolution, DataFunction::RollingPeak),
                              StatsRequest.new(host.hostname, devclass, x, counter, startTime, duration, resolution, DataFunction::RollingAverage))
            }
        else
            requestList.push( StatsRequest.new(host.hostname, devclass, 0, counter, startTime, duration, resolution, DataFunction::Average), 
                              StatsRequest.new(host.hostname, devclass, 0, counter, startTime, duration, resolution, DataFunction::Peak),
                              StatsRequest.new(host.hostname, devclass, 0, counter, startTime, duration, resolution, DataFunction::RollingPeak),
                              StatsRequest.new(host.hostname, devclass, 0, counter, startTime, duration, resolution, DataFunction::RollingAverage))
        end
    }

    times = []
    statsList = getStatsData?( requestList )
    statsList.each { |stat|
        if stat.get_status? == StatsStatus::SUCCESS
            dat = stat.get_data?
            counter  = stat.get_counter?
            function = stat.get_function?
            devClass = stat.get_devClass?
            dat.each{ |data|
	        value = _get_snapshot_value(data.get_value?, devClass, function)
                valueindex = (data.get_timestamp?.to_i - dat[0].get_timestamp?.to_i) / resolution
                times.size.upto(valueindex) { |x|
                    time = Time.at(dat[0].get_timestamp?.to_i + valueindex * resolution)
                    ts   = Date::ABBR_MONTHNAMES[time.month] + ' ' + time.day.to_s 
                    ts  += ' ' + time.hour.to_s + ':' + time.min.to_s if myDays.to_i == 1
                    times.push ts
                }
		[@avg_history, @peak_history, @roll_avg_history, @roll_peak_history].each { |valuearray|
			valuearray[:values].size.upto(valueindex) { |x|
				valuearray[:values].push 0
				valuearray[:dataPoints].push 0
			}
		}
		if function == DataFunction::Average
		    valuearray = @avg_history
                elsif function == DataFunction::Peak
		    valuearray = @peak_history
                elsif function == DataFunction::RollingAverage
		    valuearray = @roll_avg_history
                elsif function == DataFunction::RollingPeak
		    valuearray = @roll_peak_history
                end

		valuearray[:values][valueindex] = value.to_i
		valuearray[:dataPoints][valueindex] += 1
            }
        else
            RAILS_DEFAULT_LOGGER.warn("unable to find collectd/rrd stats for " + stat.get_node?.to_s)
	end
    }

    # need to average cpu instances
    if target == "cpu"
        [@avg_history, @peak_history, @roll_avg_history, @roll_peak_history].each { |valuearray|
	    0.upto(valuearray[:values].size - 1){ |x|
                valuearray[:values][x] /= valuearray[:dataPoints][x] if valuearray[:dataPoints][x] > 0
	    }
	}
    end

    total_peak = 0
    total_roll_peak = 0
    0.upto(@peak_history[:values].size - 1){ |x| total_peak = @peak_history[:values][x] if @peak_history[:values][x] > total_peak }
    0.upto(@roll_peak_history[:values].size - 1){ |x| total_roll_peak = @roll_peak_history[:values][x] if @roll_peak_history[:values][x] > total_roll_peak  }

    scale = []
    if target == "cpu"
        0.upto(100){ |x|
            scale.push x.to_s
        }
    elsif target == "memory"
        #increments = @pool.hosts.total_memory / 512
        0.upto(@pool.hosts.total_memory) { |x| 
	    if x % 1024 == 0
            	scale.push((x / 1024).to_s) # divide by 1024 to convert to MB
	    end
        }
    elsif target == "load"
        0.upto(total_peak){|x|
            scale.push x.to_s if x % 5 == 0
        }
    end

    # if no data is found, we wont have a time axis
    times = _generate_default_time_axis(myDays) if times.size == 0

    graph_object = {
       :timepoints => times,
       :scale => scale,
       :dataset => 
        [
            {
                :name => target + "roll_peak",
                :values => @roll_peak_history[:values],
                :stroke => @roll_peak_history[:color],
                :strokeWidth => 2
            },
            {
                :name => target + "roll_average",
                :values => @roll_avg_history[:values], 
                :stroke => @roll_avg_history[:color],
                :strokeWidth => 2
            },
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

    load_value = 0
    if target == 'host'
        load_value = Host.find(@id).load_average
    elsif target == 'vm'
        load_value = Vm.find(@id).host.load_average
    elsif target == 'resource'
        VmResourcePool.find(@id).vms.each { |vm|
            load_value += vm.host.load_average
        }
    end

    if load_value.nil?
        load_value = 0
    elsif load_value > 10 # hack to cap it as we have nothing to compare against
        load_value = 10 
    end
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

    @snapshots   = { :avg   => { 'load' => 0, 'cpu' => 0, 'netin' => 0, 'netout' => 0, 'memory' => 0 }, # average values to be plotted on the graph
                     :scale => { 'load' => 10, 'cpu' => 100, 'memory' => 0, 'netin' => 1000, 'netout' => 1000}, # values which to scale graphs against
                     :peak  => { 'load' => 0, 'cpu' => 0, 'netin' => 0, 'netout' => 0, 'memory' => 0 }}
    @data_points = { :avg   => { 'load' => 0, 'cpu' => 0, 'netin' => 0, 'netout' => 0, 'memory' => 0 },
                     :scale => { 'load' => 10, 'cpu' => 100, 'memory' => 0, 'netin' => 1000, 'netout' => 1000}, 
                     :peak  => { 'load' => 0, 'cpu' => 0, 'netin' => 0, 'netout' => 0, 'memory' => 0 }}

    duration = 600
    resolution = RRDResolution::Default

    # XXX DIRTYHACK hard-code nic bandwidth to 1000 to make graphs look decent
    # until we have real hardware discovery
    requestList = []
    if @target == 'host'
        host =  Host.find(@id)
        requestList += _create_host_snapshot_requests(host.hostname, duration, resolution)
        @snapshots[:scale]['memory'] = host.memory_in_mb
        host.nics.each{ |nic|
            @snapshots[:scale]['netin'] += 1000
            @snapshots[:scale]['netout'] += 1000
            # @snapshots[:scale]['netin']  += nic.bandwidth 
            # @snapshots[:scale]['netout'] += nic.bandwidth
        }
    elsif @poolType == 'vm'
        Pool.find(@id).vms.each{ |vm|
            if !vm.host.nil?
                requestList += _create_host_snapshot_requests(vm.host.hostname,  duration, resolution)
                @snapshots[:scale]['memory'] = vm.host.memory_in_mb
                vm.host.nics.each{ |nic|
                    @snapshots[:scale]['netin'] += 1000
                    @snapshots[:scale]['netout'] += 1000
                    # @snapshots[:scale]['netin']  += nic.bandwidth
                    # @snapshots[:scale]['netout'] += nic.bandwidth
                }
            end
        }
    else
        Pool.find(@id).hosts.each{ |host|
            requestList += _create_host_snapshot_requests(host.hostname,  duration, resolution)
            @snapshots[:scale]['memory'] = host.memory_in_mb
            host.nics.each{ |nic|
              @snapshots[:scale]['netin'] += 1000
              @snapshots[:scale]['netout'] += 1000
              # @snapshots[:scale]['netin']  += nic.bandwidth
              # @snapshots[:scale]['netout'] += nic.bandwidth
            }
        }
    end
    
    statsList = getStatsData?( requestList )
    statsList.each { |stat|
        if stat.get_status? == StatsStatus::SUCCESS
            devClass = stat.get_devClass?
            counter  = stat.get_counter?
            function = stat.get_function?
            stat.get_data?.each{ |data|
                value = data.get_value?
                if devClass == DEV_KEY_CLASSES["cpu"]
                    if function == DataFunction::Average
                        @snapshots[:avg]["cpu"] +=  value.to_i
                        @data_points[:avg]["cpu"] += 1
                    elsif function == DataFunction::Peak
                        @snapshots[:peak]["cpu"] =  value.to_i
                        @data_points[:peak]["cpu"] += 1
                    end
                elsif !value.nan?
                    if devClass == DEV_KEY_CLASSES["load"]
                        if function == DataFunction::Average
                            @snapshots[:avg]["load"] += value.to_i
                            @data_points[:avg]["load"] += 1
                        elsif function == DataFunction::Peak
                            @snapshots[:peak]["load"] += value.to_i
                            @data_points[:peak]["load"] += 1
                        end
                    elsif devClass == DEV_KEY_CLASSES["netout"]  && counter == DEV_KEY_COUNTERS["netout"]
                        if function == DataFunction::Average
                            @snapshots[:avg]["netout"] += (value.to_i * 8 / 1024 / 1024).to_i # mbits
                            @data_points[:avg]["netout"] += 1
                        elsif function == DataFunction::Peak
                            @snapshots[:peak]["netout"] += (value.to_i * 8 / 1024 / 1024).to_i #mbits
                            @data_points[:peak]["netout"] += 1
                        end
                   elsif devClass == DEV_KEY_CLASSES["netin"] && counter == DEV_KEY_COUNTERS["netin"]
                        if function == DataFunction::Average
                            @snapshots[:avg]["netin"] += (value.to_i * 8 / 1024 / 1024).to_i # mbits
                            @data_points[:avg]["netin"] += 1
                        elsif function == DataFunction::Peak
                            @snapshots[:peak]["netin"] += (value.to_i * 8 / 1024 / 1024).to_i # mbits
                            @data_points[:peak]["netin"] += 1
                        end
                    elsif devClass == DEV_KEY_CLASSES["memory"]
                        if function == DataFunction::Average
                            @snapshots[:avg]["memory"] += (value.to_i / 1000000).to_i
                            @data_points[:avg]["memory"] += 1
                        elsif function == DataFunction::Peak
                            @snapshots[:peak]["memory"] += (value.to_i / 1000000).to_i
                            @data_points[:peak]["memory"] += 1
                        end
                    end
                end
            }
        else
            RAILS_DEFAULT_LOGGER.warn("unable to find collectd/rrd stats for " + stat.get_node?.to_s)
        end
    }
    @snapshots[:avg]['load']    /= @data_points[:avg]['load']    if @data_points[:avg]['load']    != 0
    @snapshots[:peak]['load']   /= @data_points[:peak]['load']   if @data_points[:peak]['load']   != 0
    @snapshots[:avg]['cpu']     /= @data_points[:avg]['cpu']     if @data_points[:avg]['cpu']     != 0
    @snapshots[:peak]['cpu']    /= @data_points[:peak]['cpu']    if @data_points[:peak]['cpu']    != 0
    @snapshots[:avg]['memory']  /= @data_points[:avg]['memory']  if @data_points[:avg]['memory']  != 0
    @snapshots[:peak]['memory'] /= @data_points[:peak]['memory'] if @data_points[:peak]['memory'] != 0
    @snapshots[:avg]['netin']   /= @data_points[:avg]['netin']   if @data_points[:avg]['netin']   != 0
    @snapshots[:peak]['netin']  /= @data_points[:peak]['netin']  if @data_points[:peak]['netin']  != 0
    @snapshots[:avg]['netout']  /= @data_points[:avg]['netout']  if @data_points[:avg]['netout']  != 0
    @snapshots[:peak]['netout'] /= @data_points[:peak]['netout'] if @data_points[:peak]['netout'] != 0
  end

  private

      DEV_KEY_CLASSES  = { 'cpu' => DevClass::CPU, 'memory' => DevClass::Memory, 'disk' => DevClass::Disk,
                          'load' => DevClass::Load, 'netin' => DevClass::NIC, 'netout' => DevClass::NIC }
      DEV_CLASS_KEYS   = DEV_KEY_CLASSES.invert

      # TODO this needs fixing / completing (cpu: more than user time? disk: ?, load: correct?, nics: correct?)
      DEV_KEY_COUNTERS = { 'cpu' => CpuCounter::CalcUsed, 'memory' => MemCounter::Used, 'disk' => DiskCounter::Ops_read, 
                 'load' => LoadCounter::Load_1min, 'netin' => NicCounter::Octets_rx, 'netout' => NicCounter::Octets_tx }
      DEV_COUNTER_KEYS = DEV_KEY_COUNTERS.invert

      def _create_host_snapshot_requests(hostname, duration, resolution)
        requestList = []
        requestList << StatsRequest.new(hostname, DEV_KEY_CLASSES['memory'], 0, DEV_KEY_COUNTERS['memory'],
                                                    0, duration, resolution, DataFunction::Average) 
        requestList << StatsRequest.new(hostname, DEV_KEY_CLASSES['memory'], 0, DEV_KEY_COUNTERS['memory'], 
                                                    0, duration, resolution, DataFunction::Peak   ) 
        requestList << StatsRequest.new(hostname, DEV_KEY_CLASSES['load'],   0, DEV_KEY_COUNTERS['load'],
                                                    0, duration, resolution, DataFunction::Average)
        requestList << StatsRequest.new(hostname, DEV_KEY_CLASSES['load'],   0, DEV_KEY_COUNTERS['load'], 
                                                    0, duration, resolution, DataFunction::Peak   )
        requestList << StatsRequest.new(hostname, DEV_KEY_CLASSES['cpu'],    0, DEV_KEY_COUNTERS['cpu'], 
                                                     0, duration, resolution, DataFunction::Average) # TODO more than 1 cpu
        requestList << StatsRequest.new(hostname, DEV_KEY_CLASSES['cpu'],    0, DEV_KEY_COUNTERS['cpu'], 
                                                    0, duration, resolution, DataFunction::Peak   ) # TODO more than 1 cpu
        requestList << StatsRequest.new(hostname, DEV_KEY_CLASSES['netout'], 0, DEV_KEY_COUNTERS['netout'], 
                                                    0, duration, resolution, DataFunction::Average) 
        requestList << StatsRequest.new(hostname, DEV_KEY_CLASSES['netout'], 0, DEV_KEY_COUNTERS['netout'], 
                                                    0, duration, resolution, DataFunction::Peak   ) 
        requestList << StatsRequest.new(hostname, DEV_KEY_CLASSES['netin'],  0, DEV_KEY_COUNTERS['netin'],
                                                    0, duration, resolution, DataFunction::Average) 
        requestList << StatsRequest.new(hostname, DEV_KEY_CLASSES['netin'],  0, DEV_KEY_COUNTERS['netin'], 
                                                    0, duration, resolution, DataFunction::Peak   ) 
        return requestList
      end

      def _get_snapshot_time_params(days)
          case days.to_i
              when 1
	      	return 86400,   RRDResolution::Short
              when 7
	      	return 604800,  RRDResolution::Medium
              when 30
	        return 2592000, RRDResolution::Medium
              else
	        return 604800,  RRDResolution::Default
          end
      end

      def _get_snapshot_value(value, devClass, function)
          if ( ( devClass != DEV_KEY_CLASSES["cpu"]) && 
               ( function != DataFunction::RollingAverage)  &&
               ( function != DataFunction::RollingPeak) &&
	       ( value.nan?) ) 
                   return 0 
          end

          # massage some of the data:
          if devClass == DEV_KEY_CLASSES["cpu"]
              return value.to_i
          elsif devClass == DEV_KEY_CLASSES["netout"] && counter == DEV_KEY_COUNTER["netout"]
              return (value.to_i * 8 / 1024 / 1024).to_i #mbits
          elsif devClass == DEV_KEY_CLASSES["netin"] && counter == DEV_KEY_COUNTER["netin"]
              return (value.to_i * 8 / 1024 / 1024).to_i # mbits 
          elsif devClass == DEV_KEY_CLASSES["memory"]
              return (value.to_i / 1000000).to_i
          end
      end

      def _generate_default_time_axis(myDays)
          times = []
          now = Time.now
          if myDays.to_i == 1
              0.upto(152){|x|
                  time = now - 568 * x # 568 = 24 * 60 * 60 / 152 = secs / interval
	    	  times.push Date::ABBR_MONTHNAMES[time.month] + ' ' + time.day.to_s + ' ' + time.hour.to_s + ':' + time.min.to_s 
	      }
	  elsif
	      1.upto(myDays.to_i * 3){|x|
	    	  time = now - x * 28800 # 24 * 60 * 60 / ~2
	    	  times.push Date::ABBR_MONTHNAMES[time.month] + ' ' + time.day.to_s
	      }
	  end
	  times.reverse!
      end

end
