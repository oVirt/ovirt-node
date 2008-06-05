module TreeHelper
  def tree_html(treenode)
    if treenode[:children]
      children = %{
       <ul>
         #{treenode[:children].collect {|child| "<li>#{tree_html(child)}</li>"}.join("\n")}
       </ul>
      }
    else
      children = ""
    end
    %{ 
     <div id="tree#{treenode[:id]}">
       #{treenode[:obj][:type]} #{treenode[:obj].name}
       #{children}
     </div>
     }
  end
end
