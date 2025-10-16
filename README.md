Small app for something.

Stack:
* FastAPI
* uvicorn
* asyncio
* Postgres
* Brython


## Install and config

### Base

```bash
cd /var/www
git clone https://github.com/sphynkx/oob
cd oob
cp install/.env-sample .env
```
Modify `.env` with your own params.

### DB
Add to `/var/lib/pgsql/data/pg_hba.conf`:
```conf
# oob app
local   oob01           oob                             scram-sha-256
host    oob01           oob        127.0.0.1/32         scram-sha-256
host    oob01           oob        ::1/128              scram-sha-256
```
Replace 'ADMIN_PASSWORD' to postgres admin password and 'SECRET' to the same as in the `.env`. And run:
```bash
sudo -u postgres PGPASSWORD='ADMIN_PASSWORD'  psql -v db_user='oob' -v db_name='oob01' -v db_pass='SECRET' -f install/prep.sql
psql -U oob -d oob01 -f install/schema.sql
service postgresql restart
```


### Nginx
On external hosting server - create `/etc/nginx/conf.d/oob.conf`:
```conf
server {
        server_name  oob.sphynkx.org.ua;
        listen       80;
        access_log   /var/log/nginx/oob-access.log  main;
        error_log   /var/log/nginx/oob-error.log;
        location / {
        proxy_pass      http://192.168.7.3:8010;
        proxy_connect_timeout       600;
        proxy_send_timeout          600;
        proxy_read_timeout          600;
        send_timeout                600;
        }
}
```
Then:
```bash
service nginx restart
letsencrypt
```
Choose subdomain and set option __2__. 


### App start

```bash
chmod a+x run.sh
./run.sh
```
After first run comment out "pip install .." lines.

Check:
```bash
curl https://oob.sphynkx.org.ua/health
```
