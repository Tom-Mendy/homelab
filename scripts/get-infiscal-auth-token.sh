#̣̣!/usr/bin bash

kubectl -n infisical get secret infisical-auth-token -o jsonpath='{.data.token}' | base64 -d
