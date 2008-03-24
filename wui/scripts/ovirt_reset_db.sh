#!/bin/bash

/usr/bin/dropdb -U postgres ovirt
su - postgres -c "/usr/bin/psql -f /usr/share/ovirt-wui/psql.cmds"
cd /usr/share/ovirt-wui
rake db:migrate
