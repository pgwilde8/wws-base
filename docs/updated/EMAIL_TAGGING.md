# Email Tagging Strategy

## Overview

Brokers use **plus-addressing** (`+tag`) to sort emails by load board source. We store clean base emails in the database and dynamically add tags when sending based on where the load came from.

## How It Works

### 1. Storage (Clean Base)
- **Store:** `gcs_parade@geodis.com` (clean base, no tag)
- **Why:** Works for any load board, platform-agnostic directory

### 2. Sending (Dynamic Tagging)
- **Load from TruckSmarter:** Send to `gcs_parade+trucksmarter@geodis.com`
- **Load from DAT:** Send to `gcs_parade+dat@geodis.com`
- **Load from Truckstop:** Send to `gcs_parade+truckstop@geodis.com`
- **Unknown source:** Send to `gcs_parade@geodis.com` (clean base)

### 3. Benefits
- ✅ Broker's system sees the correct tag and sorts appropriately
- ✅ Directory stays clean (one email per broker)
- ✅ Works for any load board without manual updates

## Implementation

### Email Service (`app/services/email.py`)

**Function:** `add_load_board_tag(email, load_source)`
- Adds `+tag` to email based on load source
- Replaces existing tags if present
- Returns clean base if `load_source` is None

**Updated:** `send_negotiation_email()` now accepts `load_source` parameter

### Load Schema (`app/schemas/load.py`)

**Added:** `load_source: Optional[str]` field to track where load came from

### Usage Example

```python
from app.services.email import send_negotiation_email

# Load came from TruckSmarter
result = send_negotiation_email(
    to_email="gcs_parade@geodis.com",  # Clean base from DB
    subject="Load Inquiry",
    body="...",
    load_id="12345",
    negotiation_id=678,
    load_source="trucksmarter"  # Adds +trucksmarter tag
)
# Email sent to: gcs_parade+trucksmarter@geodis.com
```

## Load Board Tag Mapping

Common load board names → tag format:
- `trucksmarter` → `+trucksmarter`
- `dat` → `+dat`
- `truckstop` → `+truckstop`
- `123loadboard` → `+123loadboard`
- `centraldispatch` → `+centraldispatch`
- `getloaded` → `+getloaded`

Tags are normalized: lowercase, alphanumeric only (spaces/special chars removed)

## Manual Collection

When collecting emails manually from load boards:

1. **Collect:** `gcs_parade+trucksmarter@geodis.com` (with tag)
2. **Script stores:** `gcs_parade@geodis.com` (clean base)
3. **When sending:** Tag is added back based on load source

This ensures:
- Directory has clean base emails
- Emails are tagged correctly when sent
- Works for any load board
