/*
 * Async Treeview 0.1 - Lazy-loading extension for Treeview
 * 
 * http://bassistance.de/jquery-plugins/jquery-plugin-treeview/
 *
 * Copyright (c) 2007 Jörn Zaefferer
 *
 * Dual licensed under the MIT and GPL licenses:
 *   http://www.opensource.org/licenses/mit-license.php
 *   http://www.gnu.org/licenses/gpl.html
 *
 * Revision: $Id$
 *
 */

;(function($) {

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
			var link_open;
			var link_close;
			var span_onclick;
			var current = $("<li/>").attr("id", this.id || "");
			if (settings.action_type=="hyperlink"){
			    link_open = "<a href=\"" + settings.link_to + "/" + this.id + "\">";
			    link_close =  "</a>";
			} else {
			    link_open  = "";
			    link_close = "";
			}
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
//                          $('li #' + this.id + ' span > a')
//                            .bind('click', function() { 
//                              $.ajax({
//                                url: this.href,
//                                type: 'GET',
//                                data: {ajax:true},
//                                dataType: 'html',
//                                success: function(data) { 
//                                  var wrapped_data = $(data).not('div#side-toolbar');//.find('#navigation-tabs');
//                                  $('#side-toolbar').html($(data).find('div.toolbar'));
//                                  $('#tabs-and-content-container').html($(data).not('div#side-toolbar'));
//                                },
//                                error: function(xhr) {alert(xhr.status + ' ' + xhr.statusText);}
//                              })
//                              return false;
//                            });

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
                $.each(response, createNode, [child]);
                $(container).treeview({add: child});
    });
}

var proxied = $.fn.treeview;
$.fn.asynch_treeview = function(settings) {
	if (!settings.url) {
		return proxied.apply(this, arguments);
	}
	var container = this;
        settings.current_pool_id!=""?settings.params={current_id:settings.current_pool_id}:settings.params=null;
	load(settings, settings.params, this, container);        
	var userToggle = settings.toggle;
	return proxied.call(this, $.extend({}, settings, {
		collapsed: true,
		toggle: function() {
			var $this = $(this);
			if ($this.hasClass("hasChildren")) {
				var childList = $this.removeClass("hasChildren").find("ul");
                                childList.empty();
				load(settings, {id:this.id}, childList, container);
			}
			if (userToggle) {
				userToggle.apply(this, arguments);
			}
		}
	}));
};

})(jQuery);
