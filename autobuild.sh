#oVirt wui autobuild script

#run tests
cd wui/src/
rake db:migrate
rake test
