1. Save is under the logged-in driver
When you click Save on the Load Board:
The app uses your session to get the current user.
It looks up trucker_profiles by user_id and gets that driver’s trucker_id.
It then does an INSERT or ON CONFLICT (trucker_id) UPDATE into webwise.scout_status with that trucker_id, plus lanes, min_rpm, and active = true.
So the “Success” message means those parameters were stored in the DB for that logged-in driver only.
2. The driver has their own “section” in the DB (by trucker_id)
There isn’t one literal “section” per driver; their data is spread across tables but always tied to the same driver via:
webwise.trucker_profiles
One row per driver: id (this is trucker_id), user_id, display_name, mc_number, scout_api_key, etc.
webwise.scout_status
One row per driver: trucker_id (PK), lanes, min_rpm, active, updated_at.
That’s where your saved Search Parameters live.
webwise.loads
Many rows; each load the extension picks has discovered_by_id = your trucker_id. So “Scout Picked Loads” is “loads where discovered_by_id = me.”
webwise.negotiations
Many rows per driver: trucker_id + load_id (and status, rate, etc.). So each job/negotiation is tied to a driver and a load.
webwise.load_documents
Per load, per trucker: BOL, invoice, etc., keyed by trucker_id and load_id.
Other driver-scoped tables use trucker_id as well (e.g. notifications, factoring_referrals, claim_requests).
So: Search Parameters are saved under the logged-in driver, and the logged-in driver has their own data everywhere via trucker_id (and for loads, load_id for each job).