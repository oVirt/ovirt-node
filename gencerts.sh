#!/bin/bash

if [ $# -ne 1 ]; then
	echo "Usage: gencerts.sh <remote_host>"
	exit 1
fi

HOST=$1

# First generate the CA key
/usr/bin/certtool --generate-privkey > cakey.pem

cat > ca.info << EOF
cn = RedHat
ca
cert_signing_key
EOF

/usr/bin/certtool --generate-self-signed --load-privkey cakey.pem --template ca.info --outfile cacert.pem

# Next, the "server" key that will go on the ovirt host
/usr/bin/certtool --generate-privkey > serverkey.pem
cat > server.info << EOF
organization = RedHat
cn = $HOST
tls_www_server
encryption_key
signing_key
EOF

/usr/bin/certtool --generate-certificate --load-privkey serverkey.pem --load-ca-certificate cacert.pem --load-ca-privkey cakey.pem --template server.info --outfile servercert.pem

# Finally the "client" key that will go on the machine connecting via libvirt
/usr/bin/certtool --generate-privkey > clientkey.pem
cat > client.info << EOF
country = US
state = MA
locality = Boston
organization = RedHat
cn = client1
tls_www_client
encryption_key
signing_key
EOF

/usr/bin/certtool --generate-certificate --load-privkey clientkey.pem --load-ca-certificate cacert.pem --load-ca-privkey cakey.pem --template client.info --outfile clientcert.pem

echo "The CA, server, and client certificates have been generated."
echo "To finish the installation, run the following commands:"
echo
echo "# put the CA certificate in place"
echo "cp cacert.pem /etc/pki/CA"
echo "# put the serverkey where the Ovirt host can fetch them"
echo "cp serverkey.pem servercert.pem /var/www/html"
echo "# copy the client keys to the appropriate place"
echo "mkdir -p /etc/pki/libvirt/private"
echo "cp clientkey.pem /etc/pki/libvirt/private"
echo "cp clientcert.pem /etc/pki/libvirt"
