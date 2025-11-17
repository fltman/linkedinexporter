# Quick Start Guide

## TL;DR - Just Get It Running

### Step 1: Setup
```bash
./setup.sh
source venv/bin/activate
```

### Step 2: Run (with manual login)
```bash
python linkedin_exporter.py
```

### Step 3: Log in
When the browser opens, log in to LinkedIn normally (complete 2FA if you have it), then press Enter in the terminal.

**That's it!** Your posts will be exported to `exports/export_TIMESTAMP/`

---

## For 2FA Users (Two-Factor Authentication)

**You have 2FA if LinkedIn asks for a code when you log in.**

### ⚠️ Important
- **DO NOT** put credentials in `.env`
- **DO NOT** use `--email` or `--password` flags
- **ALWAYS** use manual login (the browser will open)

### The Right Way
```bash
python linkedin_exporter.py
```

When you see:
```
MANUAL LOGIN REQUIRED
Please log in to LinkedIn in the browser window.
Press Enter here when you've successfully logged in...
```

1. Go to the browser window
2. Log in to LinkedIn (enter your 2FA code)
3. Return to the terminal
4. Press Enter

### What NOT to Do
```bash
# ❌ This will NOT work with 2FA:
python linkedin_exporter.py --email user@email.com --password pass

# Error you'll see:
# "Your request to activate Remember me was not successful.
#  This is because you have 2-Factor Authentication enabled"
```

---

## Custom Export Location

### Save to Documents
```bash
python linkedin_exporter.py --output ~/Documents/LinkedIn
```

### Save to Dropbox
```bash
python linkedin_exporter.py --output ~/Dropbox/LinkedIn_Backups
```

### Or set it once in `.env`
```bash
echo "OUTPUT_DIR=~/Documents/LinkedIn" >> .env
python linkedin_exporter.py
```

---

## Export More Posts

```bash
# Default: ~100-250 posts
python linkedin_exporter.py

# Hundreds of posts: ~200-500 posts
python linkedin_exporter.py --scrolls 100

# Thousands of posts: ~400-1000+ posts
python linkedin_exporter.py --scrolls 200

# Complete archive (very large): 1000+ posts
python linkedin_exporter.py --scrolls 500
```

**Note:** More scrolls = longer export time, but for thousands of posts it's worth it!

**Tip:** LinkedIn loads 2-5 posts per scroll depending on content type (videos load slower).

---

## Common Issues

### "2-Factor Authentication enabled" error
→ Use manual login (don't provide credentials)

### No posts found
→ Try more scrolls: `--scrolls 20`

### Rate limited / captcha
→ Wait a few hours, then try again with higher delays in `.env`

### Browser doesn't open
→ Check Playwright installation: `playwright install chromium`

---

## Full Command Reference

```bash
# Basic (manual login, default settings)
python linkedin_exporter.py

# Custom output directory
python linkedin_exporter.py --output /path/to/backups

# More posts
python linkedin_exporter.py --scrolls 20

# Someone else's public profile (automatically goes to their recent activity)
python linkedin_exporter.py --profile https://www.linkedin.com/in/username/

# Or use the recent activity URL directly
python linkedin_exporter.py --profile https://www.linkedin.com/in/andersbjarby/recent-activity/all/

# Combine options
python linkedin_exporter.py \
  --output ~/Documents/LinkedIn \
  --scrolls 20
```

**Note:** The tool automatically navigates to the `/recent-activity/all/` page where all posts are displayed, even if you just provide the profile URL.

---

## What Gets Exported

```
exports/export_20250117_143022/
├── posts.json                  # All your posts with metadata
└── media/
    ├── image_a3f5d9e2b1c4.jpg  # Images (deduplicated)
    ├── video_9b4c2d8e1a7f.mp4  # Videos (deduplicated)
    └── ...
```

Each post in `posts.json` includes:
- **Clean text** (HTML stripped, whitespace normalized)
- **Author** name
- **Timestamp**
- **Hashtags** (extracted as array)
- **Mentions** (extracted as array)
- **External links** (with URL and text)
- **Images** (with local file paths)
- **Videos** (with local file paths)

**What's removed:**
- Raw HTML (unless you use `--save-raw-html`)
- Extra whitespace and formatting
- LinkedIn internal links

**Deduplication:** If you share/repost content, the same media file is only downloaded once and referenced by all posts that use it.

---

## Safety & Rate Limiting

The tool automatically:
- Waits 2-5 seconds between actions
- Scrolls like a human (down, then slightly up)
- Waits for pages to fully load
- Delays between media downloads

**To be extra safe:**
```bash
# Edit .env to increase delays
RATE_LIMIT_MIN_DELAY=5
RATE_LIMIT_MAX_DELAY=10
```

**Best practices:**
- Don't run more than once per day
- Start with fewer scrolls, increase gradually
- If you get captcha, wait several hours

---

## Need Help?

1. Check **TROUBLESHOOTING.md** for common issues
2. Check **CONFIGURATION.md** for all options
3. Check **README.md** for complete documentation

---

## Example: Complete Export

```bash
# 1. Setup (first time only)
./setup.sh
source venv/bin/activate

# 2. Configure output (optional)
echo "OUTPUT_DIR=~/Documents/LinkedIn_Backups" > .env

# 3. Run export with high scroll count for thousands of posts
python linkedin_exporter.py --scrolls 200

# 4. Log in when browser opens (complete 2FA)

# 5. Press Enter in terminal

# 6. Wait for export to complete (20-30 minutes for large archives)

# 7. Find your posts in ~/Documents/LinkedIn_Backups/export_TIMESTAMP/
```

**Time estimates:**
- 50 scrolls: ~5-10 minutes (includes expanding truncated posts)
- 100 scrolls: ~10-20 minutes
- 200 scrolls: ~20-40 minutes
- 500 scrolls: ~50-90 minutes

**Note:** The tool automatically expands all "see more" buttons to get full post text. This adds time but ensures you get complete content!

**Done!** 🎉
