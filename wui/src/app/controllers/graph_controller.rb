class GraphController < ApplicationController
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
