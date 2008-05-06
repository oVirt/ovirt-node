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

function load(settings, root, child, container) {
        var params;
        root?params={id:root}:settings.current_pool_id!=""?params={current_id:settings.current_pool_id}:null;
        //null;
	$.getJSON(settings.url, params, function(response) { //{id: root}
		function createNode(parent) {                  
                        if (this.type=="HardwarePool") {
                            settings.link_to=settings.hardware_url 
                            settings.span_class="folder";
                        } else {
                            settings.link_to=settings.resource_url;
                            settings.span_class="file";
                        }
			var current = $("<li/>").attr("id", this.id || "")
                          .html("<span class=\"" + settings.span_class + "\"><a href=\"" + settings.link_to + "/" + this.id + "\">" + this.text +  "</a></span>")
                          .appendTo(parent);
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
                child.empty();
		$.each(response, createNode, [child]);
        $(container).treeview({add: child});
    });
}

var proxied = $.fn.treeview;
$.fn.treeview = function(settings) {
	if (!settings.url) {
		return proxied.apply(this, arguments);
	}
	var container = this;
	load(settings, settings.id, this, container); //original 2nd param value was "source"
	var userToggle = settings.toggle;
	return proxied.call(this, $.extend({}, settings, {
		collapsed: true,
		toggle: function() {
			var $this = $(this);
			if ($this.hasClass("hasChildren")) {
				var childList = $this.removeClass("hasChildren").find("ul");
				load(settings, this.id, childList, container);
			}
			if (userToggle) {
				userToggle.apply(this, arguments);
			}
		}
	}));
};

})(jQuery);