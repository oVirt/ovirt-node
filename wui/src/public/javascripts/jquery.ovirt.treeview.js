;(function($) {
  var proxied = $.fn.treeview;
  $.fn.ovirt_treeview = function(settings) {
    var container = this;    
    settings.current_pool_id!=""?settings.params={current_id:settings.current_pool_id}:settings.params=null;
    load(settings, settings.params, this, container);     
    return proxied.call(this, $.extend({}, settings, {
            toggle: function() {}
    }));
  }
    
})(jQuery);

var selectedNodes = [];
var currentNode;

function load(settings, params, child, container) {
        $.getJSON(settings.url, params, function(response) { //{id: root}            
		function createNode(parent) {                     
                        if (this.type=="HardwarePool") {
                            settings.link_to=settings.hardware_url 
                            settings.span_class="folder";
                            settings.current_class = settings.current + "_folder";
                        } else {
                            settings.link_to=settings.resource_url;
                            settings.span_class="file";
                            settings.current_class = settings.current + "_file";
                        }   
			var span_onclick;
			var current = $("<li/>").attr("id", this.id || "");
			var link_open = "<a href=\"" + settings.link_to + "/" + this.id + "\">";
			var link_close =  "</a>";
			if (settings.action_type=="javascript"){
			    span_onclick = " onClick=\"" + settings.onclick + "(" + this.id + ")\" ";
   		        } else {
			    span_onclick = ""
		        }
                        if (settings.current_pool_id==this.id) {
                          current.html("<span class=\"" + settings.current_class + ">" + this.text  + "</span>")
                            .appendTo(parent);
                        } else {
                          current.html("<span class=\"" + settings.span_class + "\"" + span_onclick + ">" + link_open + this.text + link_close + "</span>")
                            .appendTo(parent);
                        }
			if (this.classes) {
				current.children("span").addClass(this.classes);
			}
			if (this.expanded) {
				current.addClass("open");
			}                        
			if (this.hasChildren || this.children && this.children.length) {
				var branch = $("<ul/>").appendTo(current);
				if (this.hasChildren) {
					current.addClass("hasChildren");
					//createNode.call({
						//classes:"placeholder",
                                        //        text:"&nbsp;",
					//	children:[]
					//}, branch);
				}
				if (this.children && this.children.length) {
					$.each(this.children, createNode, [branch])
				}
			}
		} 
                $(container).find('li').remove();
                createNode.call(response, child);                
                $(container).ovirt_treeview({add: child});
                for (var i = 0; i < selectedNodes.length; i++){
                  $('#test-tree li#' + selectedNodes[i] +' > div').click();
                }
                if (currentNode != null) {
                    var nodeType = $('li#' + currentNode + ' > span').attr('class');
                    $('li#' + currentNode + ' > span').attr('class', 'current_' + nodeType);
                }               
    });
  }    

$('#test-tree li.collapsable').livequery(
    function(){
        if($.inArray(this.id,selectedNodes) == -1){
          selectedNodes.push(this.id);
        }        
    },function(){}
); 
$('#test-tree li.expandable').livequery(
    function(){
        if($.inArray(this.id,selectedNodes) != -1){
          selectedNodes.splice(selectedNodes.indexOf(this.id),1);
        }        
    }, function(){}
); 