#!/usr/bin/env python3
"""
LinkedIn Post Exporter
Downloads your LinkedIn posts including images and videos.
"""

import os
import json
import time
import random
import re
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urlparse, parse_qs

from playwright.sync_api import sync_playwright, Page, Browser
from bs4 import BeautifulSoup
import requests
from dotenv import load_dotenv

load_dotenv()


class LinkedInExporter:
    def __init__(self, output_dir: Optional[str] = None, save_raw_html: bool = False):
        # Priority: parameter > env var > default
        if output_dir is None:
            output_dir = os.getenv("OUTPUT_DIR", "exports")
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # Rate limiting settings
        self.min_delay = float(os.getenv("RATE_LIMIT_MIN_DELAY", "2"))
        self.max_delay = float(os.getenv("RATE_LIMIT_MAX_DELAY", "5"))

        # Whether to save raw HTML (off by default to reduce file size)
        self.save_raw_html = save_raw_html

        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    def random_delay(self):
        """Add a random delay to simulate human behavior and avoid rate limiting."""
        delay = random.uniform(self.min_delay, self.max_delay)
        print(f"  Waiting {delay:.1f} seconds...")
        time.sleep(delay)

    def _clean_text(self, text: str) -> str:
        """Clean up extracted text by removing extra whitespace and normalizing."""
        if not text:
            return ""

        # Replace multiple spaces/newlines with single space
        text = re.sub(r'\s+', ' ', text)

        # Remove leading/trailing whitespace
        text = text.strip()

        # Fix common issues
        text = text.replace('\u200b', '')  # Zero-width space
        text = text.replace('\xa0', ' ')   # Non-breaking space

        return text

    def _extract_hashtags(self, text: str) -> List[str]:
        """Extract hashtags from text."""
        if not text:
            return []
        return re.findall(r'#\w+', text)

    def _extract_mentions(self, element) -> List[str]:
        """Extract @mentions from post."""
        mentions = []
        if element:
            # Look for LinkedIn profile links
            links = element.find_all('a', href=re.compile(r'/in/'))
            for link in links:
                mention_text = link.get_text(strip=True)
                if mention_text and not mention_text.startswith('#'):
                    mentions.append(mention_text)
        return mentions

    def login(self, email: Optional[str] = None, password: Optional[str] = None):
        """
        Login to LinkedIn. If credentials not provided, will pause for manual login.
        """
        print("Navigating to LinkedIn...")
        self.page.goto("https://www.linkedin.com/login")
        self.random_delay()

        email = email or os.getenv("LINKEDIN_EMAIL")
        password = password or os.getenv("LINKEDIN_PASSWORD")

        if email and password:
            print("Logging in with credentials...")
            self.page.fill('input[name="session_key"]', email)
            self.page.fill('input[name="session_password"]', password)
            self.page.click('button[type="submit"]')
            self.random_delay()

            # Wait for navigation to complete
            try:
                self.page.wait_for_load_state("load", timeout=30000)
            except Exception:
                print("  Note: Page may still be loading, continuing...")
            time.sleep(2)
        else:
            print("\n" + "="*60)
            print("MANUAL LOGIN REQUIRED")
            print("="*60)
            print("Please log in to LinkedIn in the browser window.")
            print("Press Enter here when you've successfully logged in...")
            print("="*60 + "\n")
            input()

    def navigate_to_profile(self, profile_url: Optional[str] = None):
        """Navigate to the user's recent activity page."""
        if profile_url:
            # Ensure we're going to the recent activity page
            if '/recent-activity/all/' not in profile_url:
                # Remove trailing slash if present
                profile_url = profile_url.rstrip('/')
                activity_url = f"{profile_url}/recent-activity/all/"
            else:
                activity_url = profile_url
            print(f"Navigating to recent activity: {activity_url}")
            self.page.goto(activity_url, wait_until="domcontentloaded", timeout=60000)
        else:
            print("Navigating to your recent activity...")
            # First go to profile to get the actual username
            self.page.goto("https://www.linkedin.com/in/me/", wait_until="domcontentloaded", timeout=60000)
            time.sleep(2)

            # Get the actual profile URL (LinkedIn redirects /in/me/ to actual username)
            current_url = self.page.url
            print(f"  Profile URL: {current_url}")

            # Navigate to recent activity
            if '/in/me/' in current_url:
                # Fallback if redirect didn't happen
                activity_url = "https://www.linkedin.com/in/me/recent-activity/all/"
            else:
                # Extract profile URL and add recent-activity
                base_url = current_url.rstrip('/').split('?')[0]  # Remove query params
                activity_url = f"{base_url}/recent-activity/all/"

            print(f"  Navigating to: {activity_url}")
            self.page.goto(activity_url, wait_until="domcontentloaded", timeout=60000)

        self.random_delay()

        # Wait for the page to be interactive (don't wait for networkidle as LinkedIn has continuous requests)
        try:
            self.page.wait_for_load_state("load", timeout=30000)
        except Exception as e:
            print(f"  Note: Page may still be loading background content, continuing anyway...")

        # Give the page a moment to render initial content
        time.sleep(2)

    def scroll_to_load_posts(self, num_scrolls: int = 10):
        """
        Scroll the page to load more posts.
        LinkedIn uses infinite scroll, so we need to scroll to load content.
        """
        print(f"Scrolling to load posts ({num_scrolls} scrolls)...")

        for i in range(num_scrolls):
            print(f"  Scroll {i+1}/{num_scrolls}")

            # Scroll to bottom
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            self.random_delay()

            # Scroll up a bit (more human-like)
            self.page.evaluate("window.scrollBy(0, -300)")
            time.sleep(0.5)

    def expand_all_posts(self):
        """
        Expand all 'see more' buttons to get full post text.
        Critical for getting complete content!
        """
        print("\nExpanding truncated posts to get full content...")

        # Find all "see more" buttons - LinkedIn uses various selectors
        see_more_selectors = [
            'button[aria-label*="see more"]',
            'button.feed-shared-inline-show-more-text__see-more-less-toggle',
            'button[data-tracking-control-name*="see_more"]',
            '.feed-shared-inline-show-more-text button',
            'button:has-text("see more")',
            'button:has-text("…see more")'
        ]

        expanded_count = 0
        total_buttons = 0

        # First, count total buttons
        for selector in see_more_selectors:
            try:
                buttons = self.page.query_selector_all(selector)
                for button in buttons:
                    try:
                        if button.is_visible():
                            total_buttons += 1
                    except Exception:
                        continue
            except Exception:
                continue

        print(f"  Found {total_buttons} truncated posts to expand")

        # Now expand them
        for selector in see_more_selectors:
            try:
                # Find all matching buttons
                buttons = self.page.query_selector_all(selector)

                for button in buttons:
                    try:
                        # Check if button is visible
                        if button.is_visible():
                            # Scroll button into view
                            button.scroll_into_view_if_needed()
                            time.sleep(0.3)

                            # Click to expand
                            button.click()
                            expanded_count += 1

                            # Show progress
                            if expanded_count % 10 == 0 or expanded_count == total_buttons:
                                print(f"  Expanded {expanded_count}/{total_buttons} posts...")

                            time.sleep(0.2)  # Small delay between clicks
                    except Exception:
                        # Button might have disappeared or is not clickable
                        continue

            except Exception:
                # Selector might not match anything
                continue

        print(f"  ✓ Successfully expanded {expanded_count} posts")

        # Give the page a moment to finish expanding
        time.sleep(2)

    def extract_posts(self) -> List[Dict]:
        """Extract post data from the current page."""
        print("Extracting posts from page...")

        # Get the page content
        content = self.page.content()
        soup = BeautifulSoup(content, 'html.parser')

        posts = []

        # Find all post containers
        # LinkedIn's structure may vary, these are common selectors
        post_containers = soup.find_all('div', class_=re.compile(r'feed-shared-update-v2'))

        if not post_containers:
            # Try alternative selector
            post_containers = soup.find_all('div', {'data-urn': re.compile(r'urn:li:activity:')})

        if not post_containers:
            # Try even more generic selector
            post_containers = soup.find_all('div', class_=re.compile(r'feed.*update'))

        print(f"Found {len(post_containers)} post containers")

        # Track extraction stats
        stats = {
            'with_text': 0,
            'with_author': 0,
            'with_timestamp': 0,
            'with_images': 0,
            'with_videos': 0,
            'empty': 0
        }

        for idx, post_container in enumerate(post_containers):
            try:
                post_data = self._extract_post_data(post_container, idx)
                if post_data:
                    posts.append(post_data)

                    # Track stats
                    if post_data.get('text'):
                        stats['with_text'] += 1
                    if post_data.get('author'):
                        stats['with_author'] += 1
                    if post_data.get('timestamp'):
                        stats['with_timestamp'] += 1
                    if post_data.get('images'):
                        stats['with_images'] += 1
                    if post_data.get('videos'):
                        stats['with_videos'] += 1
                    if not any([post_data.get('text'), post_data.get('images'), post_data.get('videos')]):
                        stats['empty'] += 1

                    # Show progress every 50 posts
                    if (idx + 1) % 50 == 0:
                        print(f"  Processed {idx + 1}/{len(post_containers)} posts...")
            except Exception as e:
                print(f"  Error extracting post {idx}: {e}")

        # Print extraction summary
        print(f"\nExtraction Summary:")
        print(f"  Total posts: {len(posts)}")
        print(f"  Posts with text: {stats['with_text']}")
        print(f"  Posts with author: {stats['with_author']}")
        print(f"  Posts with timestamp: {stats['with_timestamp']}")
        print(f"  Posts with images: {stats['with_images']}")
        print(f"  Posts with videos: {stats['with_videos']}")
        print(f"  Empty posts: {stats['empty']}")

        if stats['with_text'] == 0 and len(posts) > 0:
            print("\n⚠ WARNING: No text extracted from any posts!")
            print("  LinkedIn's HTML structure may have changed.")
            print("  Run: python debug_live.py")
            print("  This will help identify the correct selectors.")

        return posts

    def _extract_post_data(self, post_container, idx: int) -> Optional[Dict]:
        """Extract data from a single post container with cleaned text."""

        # Try multiple selectors for text content
        # Based on actual LinkedIn HTML structure from debug
        text_elem = None
        text_selectors = [
            ('div', re.compile(r'update-components-text')),  # Primary text container
            ('span', re.compile(r'break-words')),            # Text wrapper
            ('div', re.compile(r'feed-shared-text')),        # Old structure
        ]

        for tag, pattern in text_selectors:
            text_elem = post_container.find(tag, class_=pattern)
            if text_elem:
                break

        # If still no text, look specifically for the inline show-more container
        if not text_elem:
            show_more = post_container.find('div', class_=re.compile(r'feed-shared-inline-show-more-text'))
            if show_more:
                # The text is inside this container
                text_elem = show_more.find('span', class_=re.compile(r'break-words'))
                if not text_elem:
                    text_elem = show_more

        raw_text = text_elem.get_text(separator=' ', strip=True) if text_elem else ''

        # Clean the text
        clean_text = self._clean_text(raw_text)

        # Extract structured data
        hashtags = self._extract_hashtags(clean_text)
        mentions = self._extract_mentions(text_elem)

        # Extract timestamp - based on actual LinkedIn HTML
        timestamp = ''
        time_selectors = [
            ('span', re.compile(r'update-components-actor__sub-description')),  # Current structure
            ('span', re.compile(r'feed-shared-actor__sub-description')),        # Old structure
            ('time', None),
        ]

        for tag, pattern in time_selectors:
            if pattern:
                time_elem = post_container.find(tag, class_=pattern)
            else:
                time_elem = post_container.find(tag)

            if time_elem:
                # Get the visually-hidden version for clean text
                visually_hidden = time_elem.find('span', class_='visually-hidden')
                if visually_hidden:
                    timestamp = self._clean_text(visually_hidden.get_text())
                else:
                    timestamp = self._clean_text(time_elem.get_text())
                break

        # Extract author info - based on actual LinkedIn HTML
        author = ''
        # The author name is in update-components-actor__title or similar
        author_containers = [
            post_container.find('span', class_=re.compile(r'update-components-actor__title')),
            post_container.find('div', class_=re.compile(r'update-components-actor__meta')),
        ]

        for container in author_containers:
            if container:
                # Look for visually-hidden span (cleanest text)
                visually_hidden = container.find('span', class_='visually-hidden')
                if visually_hidden:
                    author_text = self._clean_text(visually_hidden.get_text())
                    # Remove "Verified • You" type suffixes
                    if author_text and '•' not in author_text[:30]:  # Author name shouldnt have • in first part
                        author = author_text.split('•')[0].strip()
                        break
                    elif author_text:
                        author = author_text.split('•')[0].strip()
                        break

                # Fallback to hoverable-link-text
                hoverable = container.find('span', class_=re.compile(r'hoverable-link-text'))
                if hoverable and not author:
                    author = self._clean_text(hoverable.get_text())
                    break

        # Extract images - try multiple approaches
        images = []

        # Try specific LinkedIn image classes first
        img_classes = [
            re.compile(r'feed-shared-image'),
            re.compile(r'update-components-image'),
            re.compile(r'ivm-view-attr__img'),
        ]

        for pattern in img_classes:
            img_elems = post_container.find_all('img', class_=pattern)
            for img in img_elems:
                src = img.get('src')
                if src and ('media.licdn.com' in src or 'dms.licdn.com' in src):
                    if src not in images:
                        images.append(src)

        # If no images found with specific classes, find all images with LinkedIn URLs
        if not images:
            all_imgs = post_container.find_all('img')
            for img in all_imgs:
                src = img.get('src', '')
                classes = ' '.join(img.get('class', [])).lower()

                # LinkedIn media URLs
                if any(domain in src for domain in ['media.licdn.com', 'dms.licdn.com', 'media-exp']):
                    # Skip profile pictures, icons, and small images
                    skip_patterns = [
                        'profile-displayphoto',  # Profile pictures
                        'profile-picture',
                        'avatar',               # Avatar images
                        'ic_',                  # Icons
                        'icon',
                    ]

                    if not any(pattern in src.lower() or pattern in classes for pattern in skip_patterns):
                        if src not in images:
                            images.append(src)

        # Extract videos
        videos = []
        video_elems = post_container.find_all('video')
        for video in video_elems:
            src = video.get('src')
            if src:
                videos.append(src)

        # Look for video in attributes
        video_containers = post_container.find_all('div', {'data-sources': True})
        for container in video_containers:
            sources = container.get('data-sources')
            if sources:
                videos.append(sources)

        # Extract links from text
        links = []
        if text_elem:
            link_elems = text_elem.find_all('a', href=True)
            for link in link_elems:
                href = link.get('href')
                # Skip LinkedIn internal links
                if href and not any(x in href for x in ['/in/', '/company/', '/hashtag/']):
                    links.append({
                        'url': href,
                        'text': self._clean_text(link.get_text())
                    })

        # Build clean post object
        post = {
            'id': idx,
            'text': clean_text,
            'author': author,
            'timestamp': timestamp,
            'hashtags': hashtags,
            'mentions': mentions,
            'links': links,
            'images': images,
            'videos': videos
        }

        # Optionally include raw HTML (off by default to reduce file size)
        if self.save_raw_html:
            post['raw_html'] = str(post_container)

        return post if (post['text'] or post['images'] or post['videos']) else None

    def download_media(self, posts: List[Dict], session_dir: Path):
        """Download images and videos from posts with deduplication."""
        print("\nDownloading media files...")

        media_dir = session_dir / "media"
        media_dir.mkdir(exist_ok=True)

        # Track downloaded URLs to avoid duplicates
        url_to_file = {}
        stats = {'images': 0, 'videos': 0, 'duplicates_skipped': 0}

        for post in posts:
            post_id = post['id']

            # Download images
            for img_idx, img_url in enumerate(post['images']):
                try:
                    # Check if we've already downloaded this URL
                    if img_url in url_to_file:
                        filepath = url_to_file[img_url]
                        stats['duplicates_skipped'] += 1
                        print(f"  Reusing existing image (duplicate URL)")
                    else:
                        # Create unique filename based on URL hash
                        url_hash = hashlib.md5(img_url.encode()).hexdigest()[:12]
                        filename = f"image_{url_hash}.jpg"
                        filepath = media_dir / filename
                        self._download_file(img_url, filepath)
                        url_to_file[img_url] = filepath
                        stats['images'] += 1

                    post['images'][img_idx] = {
                        'url': img_url,
                        'local_file': str(filepath.relative_to(session_dir))
                    }
                except Exception as e:
                    print(f"  Error downloading image for post {post_id}: {e}")

            # Download videos
            for vid_idx, vid_url in enumerate(post['videos']):
                try:
                    # Check if we've already downloaded this URL
                    if vid_url in url_to_file:
                        filepath = url_to_file[vid_url]
                        stats['duplicates_skipped'] += 1
                        print(f"  Reusing existing video (duplicate URL)")
                    else:
                        # Create unique filename based on URL hash
                        url_hash = hashlib.md5(vid_url.encode()).hexdigest()[:12]
                        filename = f"video_{url_hash}.mp4"
                        filepath = media_dir / filename
                        self._download_file(vid_url, filepath)
                        url_to_file[vid_url] = filepath
                        stats['videos'] += 1

                    post['videos'][vid_idx] = {
                        'url': vid_url,
                        'local_file': str(filepath.relative_to(session_dir))
                    }
                except Exception as e:
                    print(f"  Error downloading video for post {post_id}: {e}")

        print(f"\nMedia download stats:")
        print(f"  Images downloaded: {stats['images']}")
        print(f"  Videos downloaded: {stats['videos']}")
        print(f"  Duplicates skipped: {stats['duplicates_skipped']}")

    def _download_file(self, url: str, filepath: Path):
        """Download a file from URL to filepath."""
        if filepath.exists():
            print(f"  Skipping {filepath.name} (already exists)")
            return

        print(f"  Downloading {filepath.name}...")

        # Add random delay to avoid rate limiting
        time.sleep(random.uniform(0.5, 1.5))

        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()

        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

    def save_posts(self, posts: List[Dict]) -> Path:
        """Save posts to JSON file."""
        # Create session directory with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = self.output_dir / f"export_{timestamp}"
        session_dir.mkdir(exist_ok=True)

        # Save posts JSON
        posts_file = session_dir / "posts.json"
        with open(posts_file, 'w', encoding='utf-8') as f:
            json.dump(posts, f, indent=2, ensure_ascii=False)

        print(f"\nSaved {len(posts)} posts to {posts_file}")
        return session_dir

    def export(self, profile_url: Optional[str] = None, num_scrolls: int = 10,
               email: Optional[str] = None, password: Optional[str] = None):
        """
        Main export function.

        Args:
            profile_url: LinkedIn profile URL (if None, uses env var or logged-in user's profile)
            num_scrolls: Number of times to scroll to load more posts
            email: LinkedIn email (if None, uses env var or manual login)
            password: LinkedIn password (if None, uses env var or manual login)
        """
        print("="*60)
        print("LinkedIn Post Exporter")
        print("="*60)

        # Use profile from env var if not specified
        if profile_url is None:
            profile_url = os.getenv("LINKEDIN_PROFILE")
            if profile_url:
                print(f"Using profile from .env: {profile_url}")

        with sync_playwright() as p:
            # Launch browser (headless=False so you can see what's happening)
            print("Launching browser...")
            self.browser = p.chromium.launch(headless=False)
            self.page = self.browser.new_page()

            try:
                # Login
                self.login(email, password)

                # Navigate to profile
                self.navigate_to_profile(profile_url)

                # Scroll to load posts
                self.scroll_to_load_posts(num_scrolls)

                # Expand all "see more" buttons to get full content
                self.expand_all_posts()

                # Extract posts
                posts = self.extract_posts()

                if not posts:
                    print("\nNo posts found. Try adjusting the selectors or scrolling more.")
                    return

                # Save posts
                session_dir = self.save_posts(posts)

                # Download media
                self.download_media(posts, session_dir)

                # Save updated posts with media references
                posts_file = session_dir / "posts.json"
                with open(posts_file, 'w', encoding='utf-8') as f:
                    json.dump(posts, f, indent=2, ensure_ascii=False)

                print("\n" + "="*60)
                print("Export completed successfully!")
                print(f"Output directory: {session_dir}")
                print("="*60)

            finally:
                print("\nClosing browser...")
                self.browser.close()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Export LinkedIn posts with media")
    parser.add_argument("--profile", help="LinkedIn profile URL (optional)")
    parser.add_argument("--scrolls", type=int, default=50,
                       help="Number of scrolls to load posts (default: 50). Use 100+ for thousands of posts.")
    parser.add_argument("--email", help="LinkedIn email (optional)")
    parser.add_argument("--password", help="LinkedIn password (optional)")
    parser.add_argument("--output", default="exports",
                       help="Output directory (default: exports)")
    parser.add_argument("--save-raw-html", action="store_true",
                       help="Save raw HTML for each post (increases file size)")

    args = parser.parse_args()

    exporter = LinkedInExporter(
        output_dir=args.output,
        save_raw_html=args.save_raw_html
    )
    exporter.export(
        profile_url=args.profile,
        num_scrolls=args.scrolls,
        email=args.email,
        password=args.password
    )


if __name__ == "__main__":
    main()
