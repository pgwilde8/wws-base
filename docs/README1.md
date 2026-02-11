134.199.241.56:8990
134.199.241.56:8990/savings-view
134.199.241.56:8990/savings-test
134.199.241.56:8990/faq

cd /srv/projects/client/dispatch
source .venv/bin/activate

uvicorn app.main:app --host 0.0.0.0 --port 8990
uvicorn app.main:app --host 0.0.0.0 --port 8990 --reload --log-level debug --access-log

tree /srv/projects/client/dispatch
tree /srv/projects/client/dispatch/app/api/v1/__pycache__

# Do NOT commit real tokens. Use a placeholder or keep in .env / local notes only.
# git remote set-url origin https://YOUR_TOKEN@github.com/pgwilde8/dispatch.git

git add -A
git commit -m "noa"
git push -u origin main

http://134.199.241.56:8990/admin/login
Email: admin@example.com
Password: changeme123
