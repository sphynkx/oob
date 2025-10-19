#!/bin/sh
source .venv/bin/activate
python -m install.docker.create_admin
deactivate
## Check:
## sudo -u postgres psql -d oob01 -c "SELECT * FROM users WHERE role=admin;"
