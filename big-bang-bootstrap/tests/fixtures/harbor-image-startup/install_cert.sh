#!/bin/sh

set -e

# Install /etc/harbor/ssl/{component}/ca.crt to trust CA.
echo "Appending internal tls trust CA to ca-bundle ..."
for caFile in `find /etc/harbor/ssl -maxdepth 2 -name ca.crt`; do
    cat $caFile >> /etc/pki/tls/certs/ca-bundle.crt
    echo "Internal tls trust CA $caFile appended ..."
done
echo "Internal tls trust CA appending is Done."

if [[ -d /harbor_cust_cert && -n "$(ls -A /harbor_cust_cert)" ]]; then
    echo "Appending trust CA to ca-bundle ..."
    for z in /harbor_cust_cert/*; do
        case ${z} in
            *.crt | *.ca | *.ca-bundle | *.pem)
                if [ -d "$z" ]; then
                    echo "$z is directory, skip it ..."
                else
                    cat $z >> /etc/pki/tls/certs/ca-bundle.crt
                    echo " $z Appended ..."
                fi
                ;;
            *) echo "$z is Not ca file ..." ;;
        esac
    done
    echo "CA appending is Done."
fi
