# Troubleshooting Guide

## Common Issues and Solutions

### 0. Timeout Error on Navigation

**Symptoms:**
- `TimeoutError: Timeout 30000ms exceeded`
- Error occurs when navigating to profile
- "Closing browser..." appears before export completes

**Solution:**
This has been fixed in the code. The tool now uses a more lenient wait strategy that doesn't wait for all network activity to stop (which LinkedIn never does due to tracking/ads).

If you still see this:
1. Update to the latest version of the script
2. Check your internet connection
3. Try increasing the timeout in the code if needed

**Technical details:**
- Changed from `wait_for_load_state("networkidle")` to `wait_for_load_state("load")`
- LinkedIn has continuous background requests that prevent "networkidle" from ever occurring
- The "load" state waits for the DOM to be ready, which is sufficient

### 1. No Posts Found

**Symptoms:**
- Script runs but finds 0 posts
- "Found 0 post containers" message

**Possible Causes & Solutions:**

1. **LinkedIn's HTML structure changed**
   - LinkedIn frequently updates their HTML structure
   - Check the browser window - are posts visible?
   - Look at the page source to find new CSS class names

2. **Not scrolling enough**
   ```bash
   # Try more scrolls
   python linkedin_exporter.py --scrolls 20
   ```

3. **Not logged in properly**
   - Verify you're on your profile page
   - Check if posts are visible in the browser
   - Try manual login mode

**Debug Steps:**
```python
# Add debug output to see what's being found
# Edit linkedin_exporter.py, in extract_posts():
print(f"Page HTML length: {len(content)}")
print(f"Found containers: {len(post_containers)}")

# Check what classes LinkedIn is using
# Inspect element in browser and look for:
# - Article/post container divs
# - Their class names
# - Update the regex patterns accordingly
```

### 2. Login Issues

**Symptoms:**
- Can't log in with credentials
- "Invalid credentials" error
- 2FA/captcha challenges
- Error: "Your request to activate Remember me... was not successful"

**Solutions:**

1. **2FA Enabled (Most Common) ⚠️**

   If you see: *"This is because you have 2-Factor Authentication enabled"*

   **YOU MUST USE MANUAL LOGIN:**
   ```bash
   # Remove credentials from .env or don't use --email/--password
   python linkedin_exporter.py
   # Browser will open - log in with your 2FA code
   # Press Enter in terminal when done
   ```

   **Why?** LinkedIn blocks automated login for 2FA accounts (security feature).

2. **Use Manual Login (Recommended for Everyone)**
   ```bash
   # Don't provide credentials
   python linkedin_exporter.py
   # Log in manually when browser opens
   ```

3. **Captcha Challenges**
   - LinkedIn may show captcha for suspicious activity
   - Use manual login
   - Wait a few hours between export runs

4. **For Non-2FA Accounts Only**
   - Credentials in `.env` will work
   - But manual login is still safer

### 3. Media Downloads Failing

**Symptoms:**
- Images/videos not downloading
- "Error downloading media" messages
- Empty media folder

**Solutions:**

1. **Check Media URLs**
   - Look at `posts.json` - are URLs present?
   - URLs may be temporary or expired
   - Some media is from external sources (won't download)

2. **Network/Firewall Issues**
   ```python
   # Test URL manually
   import requests
   response = requests.get("YOUR_MEDIA_URL")
   print(response.status_code)
   ```

3. **LinkedIn Protection**
   - Some media requires authentication
   - Run export while logged in
   - Media URLs may have short expiration times

### 4. Rate Limiting / Blocked

**Symptoms:**
- "Too many requests" error
- Account temporarily restricted
- Captcha challenges

**Solutions:**

1. **Increase Delays**
   ```bash
   # Edit .env
   RATE_LIMIT_MIN_DELAY=5
   RATE_LIMIT_MAX_DELAY=10
   ```

2. **Reduce Scroll Count**
   ```bash
   python linkedin_exporter.py --scrolls 5
   ```

3. **Wait Before Re-running**
   - Wait several hours between exports
   - Don't run multiple exports in quick succession

4. **Split Large Exports**
   - Do smaller exports over several days
   - Export 10-20 posts at a time

### 5. Playwright Installation Issues

**Symptoms:**
- "Browser not found" error
- Playwright errors

**Solutions:**

1. **Install Playwright Browsers**
   ```bash
   playwright install chromium
   ```

2. **Permissions Issues**
   ```bash
   # On macOS/Linux
   chmod +x venv/bin/*
   ```

3. **Use System Chromium**
   ```python
   # Edit linkedin_exporter.py
   # Change:
   self.browser = p.chromium.launch(headless=False)
   # To:
   self.browser = p.chromium.launch(
       headless=False,
       executable_path='/path/to/chromium'
   )
   ```

### 6. Encoding/Unicode Issues

**Symptoms:**
- Special characters showing as �
- JSON encoding errors

**Solutions:**

Already handled in code:
```python
json.dump(posts, f, indent=2, ensure_ascii=False)
```

If still having issues:
```python
# When opening files
with open(file, 'r', encoding='utf-8') as f:
    data = json.load(f)
```

### 7. Memory Issues (Large Exports)

**Symptoms:**
- Script crashes during large exports
- "Out of memory" errors

**Solutions:**

1. **Export in Batches**
   ```bash
   # Do multiple smaller exports
   python linkedin_exporter.py --scrolls 10
   # Wait, then run again
   ```

2. **Stream Downloads**
   - Already implemented with `stream=True`
   - Chunks are 8KB

3. **Increase System Memory**
   - Close other applications
   - Use swap space

## Debugging Tips

### Enable Verbose Logging

Add to `linkedin_exporter.py`:
```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Then use throughout:
logger.debug(f"Found {len(posts)} posts")
```

### Inspect Page Source

```python
# Save page HTML for inspection
with open('debug_page.html', 'w', encoding='utf-8') as f:
    f.write(self.page.content())
```

### Check Network Activity

```python
# Log all requests
self.page.on("request", lambda request: print(f"→ {request.url}"))
self.page.on("response", lambda response: print(f"← {response.url} {response.status}"))
```

### Test Individual Components

```python
# Test just login
exporter = LinkedInExporter()
with sync_playwright() as p:
    exporter.browser = p.chromium.launch(headless=False)
    exporter.page = exporter.browser.new_page()
    exporter.login()
    input("Press Enter to close...")
```

## LinkedIn Structure Updates

If LinkedIn changes their HTML structure, you'll need to update the CSS selectors:

### Finding New Selectors

1. **Open LinkedIn in browser**
2. **Right-click a post → Inspect Element**
3. **Find the container div classes**
4. **Update in `linkedin_exporter.py`:**

```python
def extract_posts(self):
    # OLD (may not work after update)
    post_containers = soup.find_all('div', class_=re.compile(r'feed-shared-update-v2'))

    # NEW (update with current class names)
    post_containers = soup.find_all('div', class_=re.compile(r'NEW-CLASS-NAME'))
```

### Common LinkedIn Class Patterns

- Posts: `feed-shared-update-*`, `occludable-update`, `artdeco-card`
- Text: `feed-shared-text`, `break-words`, `attributed-text-segment-list`
- Images: `feed-shared-image`, `ivm-view-attr__img`, `lazy-image`
- Videos: `video-player`, `feed-shared-video`
- Timestamps: `feed-shared-actor__sub-description`, `visually-hidden`

### Testing New Selectors

```python
# Quick test
from bs4 import BeautifulSoup
with open('debug_page.html', 'r') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')

# Try different selectors
containers = soup.find_all('div', class_=re.compile(r'YOUR-PATTERN'))
print(f"Found {len(containers)} containers")
```

## Getting Help

1. **Check LinkedIn's Structure**
   - Save page HTML and inspect it
   - Look for pattern changes

2. **GitHub Issues**
   - Search existing issues
   - Create new issue with:
     - Error message
     - Command used
     - Browser console output

3. **Community Help**
   - Include debug output
   - Share (sanitized) HTML snippets
   - Mention Python/Playwright versions

## Prevention Tips

1. **Don't Export Too Often**
   - Once a week is reasonable
   - Daily exports may trigger rate limits

2. **Use Conservative Settings**
   - Start with fewer scrolls
   - Increase delays if needed

3. **Keep Dependencies Updated**
   ```bash
   pip install --upgrade -r requirements.txt
   playwright install chromium
   ```

4. **Test Before Large Exports**
   ```bash
   # Test with minimal scrolls first
   python linkedin_exporter.py --scrolls 2
   ```

5. **Monitor LinkedIn's Changes**
   - LinkedIn updates their site regularly
   - Check for error patterns after LinkedIn updates
