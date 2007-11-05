# Methods added to this helper will be available to all templates in the application.

require 'rubygems'
gem 'rails'
require 'erb'

module ApplicationHelper

   def ApplicationHelper.menubar(primary,secondary)
       # FIXME: primary and secondary are no longer used.
       # should change method signature.
       #app_root = ActionController::AbstractRequest.relative_url_root
       app_root = ""
       template = <<-EOF
       <ul class="nav">
       <li><strong><%= _("Hosts") %></strong>
	   <ul>
	   <li><A HREF="#{app_root}/not/here/yet"><%= _("View Hosts") %></A></li>
	   <li><A HREF="#{app_root}/not/here/yet"><%= _("Add a Host") %></A></li>
           </ul>
       </li>
       <li><strong><%= _("Guests") %></strong>
           <ul>
           <li><A HREF="#{app_root}/not/here/yet"><%= _("View Guests") %></A></li>
           <li><A HREF="#{app_root}/not/here/yet"><%= _("Add a Guest") %></A></li>
           </ul>
       </li>
       <li><strong><%= _("Task Queue") %></strong>
           <ul>
           <li><A HREF="#{app_root}/not/here/yet"><%= _("View Task Queue") %></A></li>
           </ul>
       </li>
       <li><strong><%= _("Tags") %></strong>
           <ul>
           <li><A HREF="#{app_root}/not/here/yet"><%= _("View Tags") %></A></li>
           <li><A HREF="#{app_root}/not/here/yet"><%= _("Add a Tag") %></A></li>
           </ul>
       </li>
       <li><strong><%= _("Users") %></strong>
           <ul>
           <li><A HREF="#{app_root}/not/here/yet"><%= _("View Users") %></A></li>
           <li><A HREF="#{app_root}/not/here/yet"><%= _("Add a User") %></A></li>
           </ul>
       </li>
       </ul>
       EOF

       html = ERB.new(template, 0, '%').result(binding)
       return "<DIV ID='navigation'>" + html + "</DIV>"


   end

end
