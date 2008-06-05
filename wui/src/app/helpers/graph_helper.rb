module GraphHelper

    # generate some json for the snapshot graph
    def snapshot_graph_json(title, snapshot, snapshot_remaining = 0)
        graph_object = {
            :timepoints => [],
            :dataset =>
            [
                {
                    :name => title,
                    :values => [snapshot],
                    :fill => snapshot.to_f / (snapshot + snapshot_remaining).to_f > 0.75 ? 'red' : 'blue',
                    :stroke => 'lightgray',
                    :strokeWidth => 1
                },
                {
                    :name => title + 'remaining',
                    :values => [snapshot_remaining],
                    :fill => 'white',
                    :stroke => 'lightgray',
                    :strokeWidth => 1 
                }
            ]
        }
        return ActiveSupport::JSON.encode(graph_object)
    end

    # figure out a remaining value that will not skew the graph
    def snapshot_graph_remaining(value)
        # TODO (adjust with increasing values?, pass in a devClass?)
        return 1024 - value
    end

    # generate some json for availability graph
    def availability_graph_json(title, total, available, used)
        color = 'blue'
        data_sets = []
        if (total > used)
            # 3/4 is the critical boundry for now
            color = 'red' if (used.to_f / total.to_f) > 0.75 
            data_sets.push ({ :name => title + '_used', :values => [used],
                              :fill => color, :stroke => 'lightgray', :strokeWidth => 1 },
                            { :name => title + '_available', 
                              :values => [available], :fill => 'white',
                              :stroke => 'lightgray', :strokeWidth => 1})
        else
            data_sets.push ({ :name => title + '_available', :values => [available],
                              :fill => 'white', :stroke => 'lightgray', :strokeWidth => 1 },
                            { :name => title + '_used', 
                              :values => [used], :fill => 'red',
                              :stroke => 'lightgray', :strokeWidth => 1})
        end
        return ActiveSupport::JSON.encode({:timepoints => [], :dataset => data_sets})
    end
  
end
