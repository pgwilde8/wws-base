# Notification sounds

Add audio files here so drivers hear sounds when notifications arrive.

## LOAD_WON Notification Sound

- **File name:** `cash-register-purchase.wav`
- **Purpose:** Cash register "cha-ching" sound for LOAD_WON notifications
- **Why:** Creates a Pavlovian response - driver hears "cha-ching" = money made, vault grew
- **Specs:** 
  - Duration: 0.5–1.5 seconds
  - Volume: 60% (audible but not jarring)
  - Format: WAV (MP3 also supported)
  - Current file: `cash-register-purchase.wav` ✅

## Browser Autoplay Handling

Browsers (especially Mobile Safari/Chrome) block autoplay until user interaction.
The dashboard includes an audio unlock mechanism:
- First tap/click anywhere unlocks audio context
- Audio plays silently at volume 0, then pauses
- This "unlocks" the audio for the rest of the session
- Subsequent notifications will play the "cha-ching" sound automatically
