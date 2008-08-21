#
# Copyright (C) 2008 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.  A copy of the GNU General Public License is
# also available at http://www.gnu.org/copyleft/gpl.html.

if File.exists? File.dirname(__FILE__) + '/../selenium.rb'
 require 'yaml'

 require File.dirname(__FILE__) + '/../test_helper'
 require File.dirname(__FILE__) + '/../selenium'

 class InterfaceTest < Test::Unit::TestCase
         def setup
          @config = YAML::load(File.open("#{RAILS_ROOT}/config/selenium.yml"))
          @site_url = "http://"+
                      @config["ovirt_wui_server"]["address"] + "/ovirt/"

          @browser = Selenium::SeleniumDriver.new(
                          @config["selenium_server"]["address"],
                          @config["selenium_server"]["port"],
                          @config["selenium_server"]["browser"],
                          @site_url,
		          15000)
          @browser.start
          @browser.open(@site_url)
         end

         def test_ovirt
            assert_equal("Dashboard", @browser.get_title())
         end

         def teardown
	        @browser.close
            @browser.stop
         end
 end

end
