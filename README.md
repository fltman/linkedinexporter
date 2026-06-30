# LinkedIn Post Exporter

[![Support me on Patreon](https://img.shields.io/badge/Patreon-Support%20my%20work-FF424D?style=flat&logo=patreon&logoColor=white)](https://www.patreon.com/AndersBjarby)

A Python tool to export your LinkedIn posts including images and videos. LinkedIn allows downloading articles but not regular posts - this tool fills that gap.

## Features

- **Export all your LinkedIn posts** with clean, stripped text content
- **Full content extraction** - automatically expands "see more" buttons to get complete text
- **Structured data extraction** - hashtags, mentions, links extracted separately
- **Clean JSON output** - no HTML clutter, normalized whitespace, minimal file size
- **Download images and videos** from your posts
- **Smart deduplication** - same media is only downloaded once even if shared/reposted
- **Rate limiting** to avoid being blocked by LinkedIn
- **Human-like behavior** with random delays between actions
- **Organized exports** with timestamped directories
- **Flexible authentication** - use credentials or manual login

## Installation

### 1. Install Python Dependencies

```bash
# Create a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### 2. Configure Environment (Optional)

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env`:
```
LINKEDIN_EMAIL=your.email@example.com
LINKEDIN_PASSWORD=your_password

OUTPUT_DIR=exports
RATE_LIMIT_MIN_DELAY=2
RATE_LIMIT_MAX_DELAY=5
```

**Configuration Options:**
- **Credentials** (optional): If not provided, the tool will pause and let you log in manually
- **Profile URL** (optional): Set `LINKEDIN_PROFILE` in `.env` to export a specific profile by default
- **Output directory**: Customize where exports are saved

Example `.env`:
```bash
# Your LinkedIn profile (optional)
LINKEDIN_PROFILE=https://www.linkedin.com/in/andersbjarby/

# Where to save exports
OUTPUT_DIR=~/Documents/LinkedIn_Backups
```

## Usage

### Basic Usage (Manual Login) - RECOMMENDED

**⚠️ If you have 2-Factor Authentication (2FA) enabled, you MUST use manual login.**

The safest and most reliable way is to let the tool open a browser and log in manually:

```bash
python linkedin_exporter.py
```

The browser will open, and you'll see:
```
MANUAL LOGIN REQUIRED
Please log in to LinkedIn in the browser window.
Press Enter here when you've successfully logged in...
```

Just log in normally in the browser (complete 2FA if needed), then press Enter in the terminal.

### With Credentials (Only for Non-2FA Accounts)

**Note:** This only works if you **do NOT** have 2-Factor Authentication enabled. If you have 2FA, use manual login above.

```bash
python linkedin_exporter.py --email your.email@example.com --password your_password
```

Or set them in `.env` and run:
```bash
python linkedin_exporter.py
```

### Configuring the Output Directory

You can configure where exports are saved in three ways (listed by priority):

**1. Command-line argument (highest priority):**
```bash
python linkedin_exporter.py --output /path/to/my/backups
```

**2. Environment variable in `.env`:**
```bash
# In .env file
OUTPUT_DIR=/Users/andersbj/Documents/LinkedIn_Backups
```

**3. Default (if not specified):**
Uses `exports/` in the current directory

**Examples:**
```bash
# Save to Documents folder
python linkedin_exporter.py --output ~/Documents/LinkedIn

# Save to external drive
python linkedin_exporter.py --output /Volumes/Backup/LinkedIn

# Use environment variable (set in .env)
OUTPUT_DIR=~/Dropbox/LinkedIn_Archive
python linkedin_exporter.py
```

Each export creates a timestamped subdirectory, so:
- `OUTPUT_DIR=backups` → saves to `backups/export_20250117_143022/`
- Multiple exports won't overwrite each other

### Advanced Options

```bash
# Export someone else's public profile
python linkedin_exporter.py --profile https://www.linkedin.com/in/username/

# Or use their recent activity URL directly
python linkedin_exporter.py --profile https://www.linkedin.com/in/andersbjarby/recent-activity/all/

# Scroll more times to load more posts (default: 50)
# For hundreds of posts:
python linkedin_exporter.py --scrolls 100

# For thousands of posts (will take longer but gets everything):
python linkedin_exporter.py --scrolls 200

# Custom output directory
python linkedin_exporter.py --output my_exports

# Combine options - full archive with many posts
python linkedin_exporter.py \
  --scrolls 200 \
  --output /Volumes/work/linkedinexport
```

### Command-line Options

- `--profile URL` - LinkedIn profile URL or recent activity URL (default: your own profile)
  - Accepts: `https://www.linkedin.com/in/username/` (automatically adds `/recent-activity/all/`)
  - Accepts: `https://www.linkedin.com/in/username/recent-activity/all/` (uses as-is)
- `--scrolls N` - Number of scrolls to load posts (default: 50)
  - 50 scrolls ≈ 100-250 posts
  - 100 scrolls ≈ 200-500 posts
  - 200 scrolls ≈ 400-1000 posts
  - For thousands of posts, use 200-500 scrolls (will take longer but worth it!)
- `--output DIR` - Output directory (default: exports)
- `--save-raw-html` - Save raw HTML for each post (default: off, increases file size significantly)
- `--email EMAIL` - LinkedIn email for login (not recommended, use manual login)
- `--password PASS` - LinkedIn password for login (not recommended, use manual login)

## Output Structure

Each export creates a timestamped directory:

```
exports/
└── export_20250117_143022/
    ├── posts.json          # All post data with metadata
    └── media/              # Downloaded media files (deduplicated)
        ├── image_a3f5d9e2b1c4.jpg
        ├── image_7e8a1b3c5d2f.jpg
        ├── video_9b4c2d8e1a7f.mp4
        └── ...
```

**Note:** Media files are named using a hash of their URL to ensure:
- Same media is only stored once (even if appears in multiple posts)
- Consistent filenames across exports
- No duplicate downloads

### posts.json Structure

```json
[
  {
    "id": 0,
    "text": "Clean post text without HTML, normalized whitespace",
    "author": "John Doe",
    "timestamp": "1w",
    "hashtags": ["#AI", "#MachineLearning"],
    "mentions": ["Jane Smith", "Tech Corp"],
    "links": [
      {
        "url": "https://example.com/article",
        "text": "Read more"
      }
    ],
    "images": [
      {
        "url": "https://media.licdn.com/...",
        "local_file": "media/image_a3f5d9e2b1c4.jpg"
      }
    ],
    "videos": [
      {
        "url": "https://video.licdn.com/...",
        "local_file": "media/video_9b4c2d8e1a7f.mp4"
      }
    ]
  }
]
```

**Key features:**
- **Clean text** - HTML stripped, whitespace normalized, no extra characters
- **Structured data** - Hashtags and mentions extracted separately
- **Author info** - Who posted it
- **External links** - URLs shared in the post (LinkedIn internal links filtered out)
- **No raw HTML** - By default, raw HTML is excluded to reduce file size
  - Add `--save-raw-html` flag if you need the original HTML

**Important:** If multiple posts share the same image or video (e.g., reposts), they will all reference the same `local_file` path, saving disk space.

## How It Works

1. **Browser Automation**: Uses Playwright to open a real browser
2. **Authentication**: Logs in using credentials or manual login
3. **Recent Activity Navigation**: Goes to your (or specified) LinkedIn recent activity page
   - For your own profile: `https://www.linkedin.com/in/{username}/recent-activity/all/`
   - This page shows all posts in chronological order
4. **Infinite Scroll**: Scrolls the page multiple times to load more posts
5. **Post Expansion**: Clicks all "see more" buttons to expand truncated posts
   - **Critical step!** LinkedIn truncates long posts in the feed
   - Ensures you get complete text, not just the first few lines
   - Also reveals all media attachments
6. **Content Extraction**: Parses HTML to extract post data
7. **Smart Media Download**: Downloads images and videos with deduplication
   - Uses URL-based deduplication to avoid downloading the same file multiple times
   - Filenames based on content hash for consistency
   - Multiple posts sharing the same media reference the same file
8. **Data Storage**: Saves everything in a structured format

## Rate Limiting

The tool implements several rate limiting strategies to avoid being blocked:

- **Random delays** between actions (2-5 seconds by default)
- **Human-like scrolling** (scroll down, slight scroll up)
- **Delays between media downloads** (0.5-1.5 seconds)
- **Network idle waiting** to ensure pages fully load

You can adjust delays in `.env`:
```
RATE_LIMIT_MIN_DELAY=3
RATE_LIMIT_MAX_DELAY=7
```

## Tips

### Get More Posts
- **For thousands of posts:** Use `--scrolls 200` or higher
- **Start with a test:** Use `--scrolls 10` first to see how many posts you get
- **Calculate your needs:** LinkedIn loads 2-5 posts per scroll
  - Want 500 posts? Use `--scrolls 100-250`
  - Want 1000 posts? Use `--scrolls 200-500`
- **Be patient:** Large exports (200+ scrolls) take 20-30 minutes but are worth it!

### Avoid Being Blocked
- **Spacing:** Wait at least a few hours between exports (daily is safer)
- **Conservative first run:** Start with `--scrolls 50-100` to test
- **Increase delays for large exports:** Edit `.env` to increase rate limits
- **Split very large archives:** Do 200 scrolls today, 200 more tomorrow

### Troubleshooting

**No posts found:**
- LinkedIn's HTML structure may have changed - check the console output
- Try scrolling more with `--scrolls 20`
- Check if you're properly logged in

**Login fails:**
- Use manual login mode (don't provide credentials)
- LinkedIn may require 2FA - use manual login
- Check credentials in `.env` file

**Media not downloading:**
- Some media URLs may be temporary or protected
- Check the `posts.json` for URLs - they may have expired
- Run the export while logged in for best results

**Rate limited:**
- Wait a few hours before trying again
- Increase delays in `.env`
- Reduce number of scrolls

## Security Notes

- **Never commit `.env` file** - it's in `.gitignore`
- **Use app-specific passwords** if available
- **Consider manual login** for better security
- **Exported data is local** - manage it securely

## Limitations

- Only exports posts visible on your profile page
- Some videos may be embedded from external sources
- Timestamp format is as displayed on LinkedIn (relative, like "1w")
- LinkedIn's HTML structure may change, requiring updates

## Legal & Ethical Considerations

- **Only export your own data** or public profiles you have permission to archive
- **Respect LinkedIn's Terms of Service**
- **Don't use for spam or harassment**
- **Use reasonable rate limits** to avoid overloading LinkedIn's servers
- This tool is for personal archival purposes

## Cleaning Up Old Exports

If you have exports from before the clean text feature was added, you can clean them up:

```bash
# See what would change (dry run)
python clean_old_export.py /Volumes/work/linkedinexport/export_20251117_010005

# Actually clean it
python clean_old_export.py /Volumes/work/linkedinexport/export_20251117_010005 --execute
```

This removes raw HTML and normalizes text, typically reducing file size by 50-80%.

## Future Improvements

Potential enhancements:
- [ ] Export post comments and reactions
- [ ] Better timestamp parsing (convert to actual dates)
- [ ] Resume from previous exports
- [ ] Export to other formats (HTML, Markdown)
- [ ] More robust error handling
- [ ] Progress bar for downloads
- [ ] Parallel media downloads (with rate limiting)

## Contributing

Found a bug or want to add a feature? Issues and pull requests welcome!

## License

CC-BY Anders Bjarby