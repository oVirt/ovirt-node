#!/bin/bash
DATABASE="invirt"
PW_FILE="/etc/invirt-wui/db/dbaccess"  
USERNAME="invirt"
EXISTS_FILE="/etc/invirt-wui/db/exists" 

#generate pg user password
PASSWD=$(/usr/bin/pwgen -1 -n 8 -s) # create random password
echo $PASSWD\n > $PW_FILE

#drop old db
/usr/bin/dropdb $DATABASE

#create new DB
/usr/bin/createdb $DATABASE


psql --dbname $DATABASE <<EOF
    DROP ROLE $USERNAME;
    CREATE ROLE $USERNAME LOGIN PASSWORD '$PASSWD'
    NOINHERIT
    VALID UNTIL 'infinity';
    GRANT ALL ON DATABASE $DATABASE TO $USERNAME;
EOF

touch $EXISTS_FILE
