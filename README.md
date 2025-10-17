Small app for something.

Stack:
* FastAPI
* uvicorn
* asyncio
* Postgres
* Brython
* Oauth2


## Install and config

### Base

```bash
cd /var/www
git clone https://github.com/sphynkx/oob
cd oob
cp install/.env-sample .env
```
Modify `.env` with your own params.

Go to [Google Cloud Console](https://console.cloud.google.com/), create new Web-app, config it, get secrets, set them to `.env` also.

Go to [Twiter Dev Portal](https://developer.x.com/en/portal/petition/essential/basic-info), create new Web-app, config it, get secrets, set them to `.env` also.


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
sudo -u postgres psql -d oob01  -f install/schema.sql
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


### Systemd

If everything is OK configure service:
```bash
cp install/systemd/oob.service /etc/systemd/system/oob.service
systemctl daemon-reload
systemctl enable oob.service
systemctl start oob.service
```


## Docker install

### Preconfig

Copy sample files:
```bash
cp install/docker/.env-sample install/docker/.env
cp install/docker/.env.db-sample install/docker/.env.db
```
and set all necessary values (JWT_SECRET, POSTGRES_PASSWORD, etc.)


### Build and run

Build images and start containers:
```bash
cd install/docker
docker compose -f docker-compose.yml up -d --build
```
Check logs:
```bash
docker compose -f install/docker/docker-compose.yml logs -f app
docker compose -f install/docker/docker-compose.yml logs -f db
```

### Access

http://localhost:8010
