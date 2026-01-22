# How to Update Midland ICI Authorization Token

The Midland API uses a Bearer token for authentication. This token expires periodically and needs to be refreshed.

## Steps to Get New Token

### 1. Open Midland ICI Website in Browser
- Go to https://www.midlandici.com.hk/
- Use Chrome or Edge browser

### 2. Open Developer Tools
- Press `F12` (Windows) or `Cmd+Option+I` (Mac)
- Go to the "Network" tab

### 3. Search for Transactions
- On the Midland website, search for any commercial transaction
- Set date range to recent dates
- Click search

### 4. Find the API Request
- In Network tab, look for a request to `transaction` or `search/v1/transaction`
- Click on it

### 5. Copy the Authorization Header
- In the request headers, find `Authorization: Bearer eyJ...`
- Copy the full token (starts with `eyJhbGciOiJSUzI1NiJ9...`)

### 6. Update the Code

Open `utils/midland_api_scraper.py` and replace line 21:

```python
self.auth_token = "Bearer eyJ[YOUR_NEW_TOKEN_HERE]"
```

## Example

Current (expired):
```python
self.auth_token = "Bearer eyJhbGciOiJSUzI1NiJ9.eyJndWlkIjoiaWNpLUVGZj..."
```

New (your token):
```python
self.auth_token = "Bearer eyJhbGciOiJSUzI1NiJ9.eyJndWlk[...your new token...]"
```

## Test After Update

```bash
python main.py --quick
```

You should see:
```
→ API returned dates (first 10): 2026-01-12, 2026-01-13, 2026-01-14...
→ Kept 50 transactions within 2026-01-12 to 2026-01-18
```

## Current Fallback Behavior

If the token is expired, the scraper now:
- ✅ Still runs (doesn't crash)
- ✅ Shows warning about wrong dates
- ✅ Keeps the data anyway (so you get SOME commercial transactions)
- ⚠️  But dates will be wrong (old data)

To get **correct dates**, you MUST update the token.

## Alternative: Disable Midland API

If you don't want to update the token, you can comment out the Midland API scraping in `main.py` and rely only on Centaline data.
