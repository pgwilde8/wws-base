134.199.241.56:8990
134.199.241.56:8990/savings-view
134.199.241.56:8990/savings-test
134.199.241.56:8990/faq
134.199.241.56:8990/savings-view 

cd /srv/projects/client/dispatch
source .venv/bin/activate

uvicorn app.main:app --host 0.0.0.0 --port 8990
uvicorn app.main:app --host 0.0.0.0 --port 8990 --reload --log-level debug --access-log

tree /srv/projects/client/dispatch
tree /srv/projects/client/dispatch/app/api/v1/__pycache__

# Do NOT commit real tokens. Use a placeholder or keep in .env / local notes only.
# git remote set-url origin https://YOUR_TOKEN@github.com/pgwilde8/dispatch.git

git add -A
git commit -m "enhances2"
git push -u origin main

http://134.199.241.56:8990/admin/login
Email: admin@example.com
Password: changeme123
---
Go to http://134.199.241.56:8990/login/client
Enter:
Email: driver@test.com
Password: test123


Your Key: 41713b4c27074cdf51f08ba1906e860f9205ec66f14f0ac90b115decf2233c3c

-- Replace 'XXXXXX' with the MC number for Online Freight
INSERT INTO webwise.brokers (mc_number, company_name, primary_email, source)
VALUES ('XXXXXX', 'Online Freight', 'imills@onlinefreight.com', 'manual')
ON CONFLICT (mc_number) DO UPDATE 
SET primary_email = EXCLUDED.primary_email,
    source = 'manual';

SELECT 
    COUNT(*) as total_brokers,
    COUNT(primary_email) as with_emails,
    COUNT(*) - COUNT(primary_email) as hollow_leads,
    ROUND((COUNT(primary_email)::numeric / COUNT(*)) * 100, 2) as success_rate_percentage
FROM webwise.brokers;    

python3 scripts/add_broker_contact.py --mc 315784 --email imills@onlinefreight.com    

connect: psql "postgresql://wws-admin:WwsAdmin2026%21@localhost/wws_dispatch_db"



nematches@ntgfreight.com
python3 scripts/add_broker_contact.py --mc 567093 --email nematches@ntgfreight.com 
python3 app/scripts/add_broker_contact.py --mc 567093 --email nematches@ntgfreight.com
PYTHONPATH=. python3 app/scripts/add_broker_contact.py --mc 567093 --email nematches@ntgfreight.com

-----------+------------------------------------------------+----------
 201805    | MARK E LYMAN                                   | FMCSA
 201667    | ALL TRUCKING INC                               | FMCSA
 201684    | TRIANGLE WAREHOUSE & DISTRIBUTION SERVICES INC | FMCSA
 216528    | KRISKA HOLDINGS LTD                            | FMCSA
 182576    | JOES TRUCKING INC                              | FMCSA
 189735    | T D Y FREIGHT SERVICES LTD                     | FMCSA
 177505    | LANDSTAR GEMINI INC                            | FMCSA
 167354    | A & J TRUCKING & WAREHOUSING INC               | FMCSA
 159819    | LSC COMMUNICATIONS LOGISTICS LLC               | FMCSA
 187735    | ALTOM TRANSPORT INC                            | FMCSA
 202448    | MCPHERSON BROS INC                             | FMCSA
 201703    | ACTIVE TRANSPORTATION COMPANY LLC              | FMCSA
 202212    | TRIANGLE DISTRIBUTION INC                      | FMCSA
 175731    | NORTH BERGEN REX TRANSPORT INC                 | FMCSA
 199051    | GREATWIDE DEDICATED TRANSPORT III LLC          | enriched
 567093    |                                                | enriched

 /srv/projects/client/dispatch/app/scripts
 python3 app/scripts/ingest_active_brokers.py
 PYTHONPATH=. python3 app/scripts/ingest_active_brokers.py

 "[Company Name]" MC [MC_Number] dispatch email

"[Company Name]" carrier packet email

"[Company Name]" setup@ or "[Company Name]" loads@

 mc_number |           company_name            |    phy_city     | phy_state | primary_phone 
-----------+-----------------------------------+-----------------+-----------+---------------
 1623537   | 1 CHOICE LOGISTICS LLC            | MIAMI           | FL        | 
 1503482   | 123 AUTO TRANSPORT LLC            | SARASOTA        | FL        | 
 1293132   | 18BRIGS LLC                       | MONROE TWP      | NJ        | 
 1764862   | 1LEV LLC                          | SAINT AUGUSTINE | FL        | 
 939953    | 1ST CLASS AUTO TRANSPORTATION INC | MIRAMAR         | FL        | 
 819175    | 1ST COAST CARGO INC.              | JACKSONVILLE    | FL        | 
 1382487   | 1ST LOGISTICS INC                 | FLEMING ISLAND  | FL        | 
 799000    | 2 J'S AUTO TRANSPORT INC.         | LAKE PARK       | FL        | 
 1604141   | 24 HOUR FREIGHT LLC               | DEERFIELD BEACH | FL        | 
 1629455   | 24 SEVEN SHIPPING INC             | LAND O LAKES    | FL        | 
(10 rows)
 "1 CHOICE LOGISTICS LLC" MC 1623537 dispatch email

"[Company Name]" carrier packet email

"[Company Name]" setup@ or "[Company Name]" loads@

SELECT mc_number, company_name, primary_email
FROM webwise.brokers
WHERE mc_number = '271691';

cd /srv/projects/client/dispatch

UPDATE webwise.brokers
SET primary_email = 'availableloads@triplettransport.com', source = 'enriched', updated_at = now()
WHERE mc_number = '271691';

SELECT mc_number, company_name, primary_email FROM webwise.brokers WHERE mc_number = '567093';

# Test with first 10 brokers (dry-run)
PYTHONPATH=. python3 app/scripts/enrich_broker_websites.py --limit 10 --dry-run

# Actually update first 100 brokers
PYTHONPATH=. python3 app/scripts/enrich_broker_websites.py --limit 100

# Process all brokers (will take a while - ~1.5s per broker = ~10 hours for 25k)
PYTHONPATH=. python3 app/scripts/enrich_broker_websites.py

************


Option 2: Smart selection (recommended)
Choose email based on load origin:
westmatches@ → for loads originating in/near West Coast
nematches@ → for loads originating in/near Northeast
charleston@ → for loads near Charleston
Pros: More targeted, professional
Cons: Requires origin matching logic
*************************************

GENPRO INC
Contact Phone:
(201) 729-9400

So the right approach is:
Use the FMCSA API to enrich all 25k with phone and address.
Use DAT + Truckstop to get the correct per-load contact when you actually see a posting, and capture those over time if you want a richer dispatch contact DB.
That’s about $90–95/mo for both boards plus free FMCSA enrichment, and matches what you’re trying to do
 