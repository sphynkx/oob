Small app for something.

Stack:
* FastAPI
* uvicorn
* asyncio
* Postgres
* Brython
* Oauth2
* Docker

Below is a native installation with separate hosting. Next also the Docker installation steps.



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

Check on server side (set your creds):
```bash
curl https://oob.sphynkx.org.ua/health
ACCESS_TOKEN=$(curl -s -X POST https://oob.sphynkx.org.ua/auth/login -H "Content-Type: application/json" -c cookies.txt -d '{"email":"no@thankx.com","password":"Reendav8"}' | jq -r .access_token); echo "$ACCESS_TOKEN"
curl -s https://oob.sphynkx.org.ua/auth/me -H "Authorization: Bearer $ACCESS_TOKEN"
curl -s https://oob.sphynkx.org.ua/api/products -H "Authorization: Bearer $ACCESS_TOKEN" | jq
curl -s https://oob.sphynkx.org.ua/api/products/6 -H "Authorization: Bearer $ACCESS_TOKEN" | jq
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

For login via social network accounts you need to go to Dev portals, create separate apps for docker installation - same as described above. Receive tokens and keys, set them to `install/docker/.env`

For initial local admin user set your credits into `ADMIN_EMAIL` and `ADMIN_PASSWORD` params.


### Build and run

Build images and start containers, create admin user for local auth.:
```bash
cd install/docker
docker compose -f docker-compose.yml up -d --build
docker compose run --rm -it app python -m install.docker.create_admin
```
Check users and logs:
```bash
docker compose exec -T db psql -U oob -d oob01 -c "SELECT * FROM users;"
docker compose -f install/docker/docker-compose.yml logs -f app
docker compose -f install/docker/docker-compose.yml logs -f db
```
Requests (cmd version, set your creds):
```
for /f "delims=" %A in ('curl -s -X POST http://localhost:8010/auth/login -H "Content-Type: application/json" -c cookies.txt -d "{\"email\":\"E@MAIL\",\"password\":\"PASSWORD\"}" ^| jq -r .access_token') do set ACCESS_TOKEN=%A
curl -s http://localhost:8010/auth/me -H "Authorization: Bearer $ACCESS_TOKEN"
curl -s http://localhost:8010/api/products -H "Authorization: Bearer %ACCESS_TOKEN%" | jq
curl -s http://localhost:8010/api/products/1 -H "Authorization: Bearer %ACCESS_TOKEN%" | jq

```


### Access

http://localhost:8010
