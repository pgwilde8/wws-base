134.199.241.56:8990
cd /srv/projects/client/dispatch
source .venv/bin/activate

uvicorn app.main:app --host 0.0.0.0 --port 8990

tree /srv/projects/client/dispatch
tree /srv/projects/client/dispatch/app/api/v1/__pycache__

# Do NOT commit real tokens. Use a placeholder or keep in .env / local notes only.
# git remote set-url origin https://YOUR_TOKEN@github.com/pgwilde8/dispatch.git

git add -A
git commit -m "Your message"
git push -u origin main
