# Install dependencies
!pip install aiohttp pandas beautifulsoup4 tqdm requests-html backoff fake-useragent

import aiohttp
import asyncio
import pandas as pd
from bs4 import BeautifulSoup
import re
import random
import time
from tqdm.asyncio import tqdm_asyncio
from google.colab import files
from fake_useragent import UserAgent
import backoff
from urllib.parse import urlparse
import logging
import json

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Generate random user agents for each request to avoid detection
ua = UserAgent()

# Function to get random headers
def get_random_headers():
    return {
        'User-Agent': ua.random,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

# Clean and fix URLs
def clean_url(url):
    url = url.strip()
    if not url.startswith("http"):
        url = "https://" + url
    
    # Parse URL to validate
    parsed = urlparse(url)
    if not parsed.netloc or not parsed.scheme:
        return None
    
    # Ensure it's a Medium article URL
    if not ('medium.com' in parsed.netloc or 
            'towardsdatascience.com' in parsed.netloc or
            'betterhumans.pub' in parsed.netloc or
            any(domain in parsed.netloc for domain in ['medium', 'towardsdatascience', 'betterhumans'])):
        logger.warning(f"Not a recognized Medium domain: {url}")
    
    return url

# Upload CSV file
def upload_and_read_csv():
    print("Please upload your CSV file with Medium URLs...")
    uploaded = files.upload()  # Opens file picker
    if not uploaded:
        raise ValueError("No file was uploaded")
    
    file_path = list(uploaded.keys())[0]  # Get uploaded file name
    logger.info(f"Processing file: {file_path}")
    
    # Read URLs from CSV
    try:
        df = pd.read_csv(file_path, header=None)
        urls = df.iloc[:, 0].dropna().tolist()
        valid_urls = []
        
        for url in urls[:500]:  # Limit to 500
            clean = clean_url(url)
            if clean:
                valid_urls.append(clean)
            else:
                logger.warning(f"Invalid URL skipped: {url}")
        
        logger.info(f"Found {len(valid_urls)} valid URLs out of {len(urls[:500])}")
        return valid_urls
    except Exception as e:
        logger.error(f"Error reading CSV: {str(e)}")
        raise

# Exponential backoff for retries
@backoff.on_exception(backoff.expo, 
                     (aiohttp.ClientError, asyncio.TimeoutError),
                     max_tries=5,
                     max_time=60)
async def fetch_html_with_backoff(session, url, delay=True):
    if delay:
        # Add random delay to avoid rate limiting
        await asyncio.sleep(random.uniform(1, 3))
    
    async with session.get(url, headers=get_random_headers(), timeout=20) as response:
        if response.status == 200:
            return await response.text()
        elif response.status == 429:  # Too Many Requests
            retry_after = int(response.headers.get('Retry-After', 30))
            logger.warning(f"Rate limited on {url}, waiting for {retry_after} seconds")
            await asyncio.sleep(retry_after)
            # Retry without additional delay
            return await fetch_html_with_backoff(session, url, delay=False)
        else:
            logger.warning(f"Failed to fetch {url}, status: {response.status}")
            return None

# Extract article details with improved parsing
def parse_article(html, url):
    if not html:
        return None
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # Try multiple selectors for title to increase chances of finding it
    title = None
    for selector in ['h1', 'h1.pw-post-title', '.graf--title']:
        title = soup.select_one(selector)
        if title:
            break
    
    # Try to find subtitle
    subtitle = None
    for selector in ['h2', 'h2.pw-subtitle', '.graf--subtitle']:
        subtitle = soup.select_one(selector)
        if subtitle:
            break
    
    # Try multiple approaches to find author
    author = "Unknown"
    author_url = ""
    
    # Method 1: Check meta tags
    author_elem = soup.find('meta', {'name': 'author'})
    if author_elem and author_elem.get('content'):
        author = author_elem['content'].strip()
    
    # Method 2: Check schema.org metadata
    schema_script = soup.find('script', {'type': 'application/ld+json'})
    if schema_script:
        try:
            schema_data = json.loads(schema_script.string)
            if isinstance(schema_data, dict):
                if 'author' in schema_data:
                    if isinstance(schema_data['author'], dict) and 'name' in schema_data['author']:
                        author = schema_data['author']['name']
                    elif isinstance(schema_data['author'], list) and len(schema_data['author']) > 0:
                        if 'name' in schema_data['author'][0]:
                            author = schema_data['author'][0]['name']
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            logger.debug(f"Error parsing JSON-LD data: {str(e)}")
    
    # Method 3: Check for author link
    for author_selector in ['a[rel="author"]', 'a.author', 'a[href*="/@"]']:
        author_link = soup.select_one(author_selector)
        if author_link:
            if author == "Unknown" and author_link.get_text(strip=True):
                author = author_link.get_text(strip=True)
            
            if 'href' in author_link.attrs:
                author_url = author_link['href']
                # Fix relative URLs
                if author_url and not author_url.startswith('http'):
                    if author_url.startswith('/@'):
                        author_url = f"https://medium.com{author_url}"
                    else:
                        parsed = urlparse(url)
                        author_url = f"{parsed.scheme}://{parsed.netloc}{author_url}"
                break
    
    # Extract title text
    title_text = title.get_text(strip=True) if title else "No title"
    subtitle_text = subtitle.get_text(strip=True) if subtitle else ""
    
    # Extract article text with better handling of article structure
    paragraphs = []
    content_selectors = ['article', '.section-content', '.section-inner']
    
    for selector in content_selectors:
        content_area = soup.select_one(selector)
        if content_area:
            for p in content_area.find_all(['p', 'h2', 'h3', 'blockquote', 'li']):
                paragraphs.append(p.get_text(strip=True))
            break
    
    # If we didn't find content with selectors, fall back to grabbing all paragraphs
    if not paragraphs:
        paragraphs = [p.get_text(strip=True) for p in soup.find_all(['p', 'h2', 'h3', 'blockquote'])]
    
    content = ' '.join(paragraphs)
    
    # Extract claps with multiple methods
    claps = "0"
    # Method 1: Look for clap count in script tags
    claps_script = soup.find('script', string=re.compile(r'"clapCount":\d+'))
    if claps_script:
        match = re.search(r'"clapCount":(\d+)', claps_script.string)
        if match:
            claps = match.group(1)
    
    # Method 2: Look for clap count in response buttons
    if claps == "0":
        clap_button = soup.select_one('button[data-action="show-recommends"]')
        if clap_button:
            clap_text = clap_button.get_text(strip=True)
            clap_match = re.search(r'(\d+)', clap_text)
            if clap_match:
                claps = clap_match.group(1)
    
    # Extract reading time with multiple methods
    reading_time = "Unknown"
    # Method 1: Look for standardized reading time text
    for rt_pattern in [re.compile(r'\d+ min read'), re.compile(r'\d+ minute read')]:
        reading_time_elem = soup.find(string=rt_pattern)
        if reading_time_elem:
            reading_time = reading_time_elem.strip()
            break
    
    # Method 2: Look for reading time in meta tags
    if reading_time == "Unknown":
        rt_meta = soup.find('meta', {'name': 'twitter:data1'})
        if rt_meta and 'content' in rt_meta.attrs and 'min read' in rt_meta['content']:
            reading_time = rt_meta['content']
    
    # Extract images with better handling of Medium's image patterns
    images = []
    
    # Look for standard img tags
    for img in soup.find_all('img'):
        if 'src' in img.attrs:
            # Filter out tiny images and icons
            if not ('icon' in img.get('class', []) or 
                   'icon' in img.get('src', '') or
                   'logo' in img.get('src', '')):
                images.append(img['src'])
    
    # Look for figure elements with background images
    for figure in soup.find_all('figure'):
        if 'style' in figure.attrs and 'background-image' in figure['style']:
            img_match = re.search(r'url\([\'"]?(.*?)[\'"]?\)', figure['style'])
            if img_match:
                images.append(img_match.group(1))
    
    images_text = '|'.join(images)
    
    # Extract published date
    published_date = "Unknown"
    # Method 1: Look for time element
    time_elem = soup.find('time')
    if time_elem and 'datetime' in time_elem.attrs:
        published_date = time_elem['datetime']
    else:
        # Method 2: Look for publication date in meta tags
        date_meta = soup.find('meta', {'property': 'article:published_time'})
        if date_meta and 'content' in date_meta.attrs:
            published_date = date_meta['content']
    
    # Extract publication/collection name
    publication = "Medium"
    publication_elem = soup.select_one('.pw-publication-name, .publication-name')
    if publication_elem:
        publication = publication_elem.get_text(strip=True)
    
    return {
        'url': url,
        'title': title_text,
        'subtitle': subtitle_text,
        'content': content,
        'author': author,
        'author_url': author_url,
        'claps': claps,
        'reading_time': reading_time,
        'images': images_text,
        'published_date': published_date,
        'publication': publication
    }

# Process a single URL with improved error handling
async def process_url(session, url, semaphore):
    async with semaphore:
        try:
            logger.info(f"Processing: {url}")
            html = await fetch_html_with_backoff(session, url)
            if html:
                article_data = parse_article(html, url)
                if article_data and article_data['title'] != "No title":
                    logger.info(f"Successfully scraped: {article_data['title']}")
                    return article_data
                else:
                    logger.warning(f"Failed to parse article from {url}")
                    return None
            else:
                logger.warning(f"No HTML received for {url}")
                return None
        except Exception as e:
            logger.error(f"Error processing {url}: {str(e)}")
            return None

# Main scraper function with improved concurrency and error handling
async def scrape_articles(urls):
    scraped_data = []
    failed_urls = []
    
    # Create a semaphore to limit concurrent requests
    semaphore = asyncio.Semaphore(5)  # Reduced from 10 to avoid rate limiting
    
    # Configure session with TCP connector to reuse connections
    conn = aiohttp.TCPConnector(limit=10, ssl=False)
    timeout = aiohttp.ClientTimeout(total=60)
    
    async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
        tasks = [process_url(session, url, semaphore) for url in urls]
        
        results = []
        # Process URLs with progress bar
        for task in tqdm_asyncio(asyncio.as_completed(tasks), total=len(tasks), desc="Scraping articles"):
            result = await task
            results.append(result)
        
        # Process results
        for i, result in enumerate(results):
            if result:
                scraped_data.append(result)
            else:
                failed_urls.append(urls[i] if i < len(urls) else "Unknown URL")
    
    return scraped_data, failed_urls

# Main execution function
async def main():
    try:
        # Get URLs from uploaded CSV
        urls = upload_and_read_csv()
        
        if not urls:
            logger.error("No valid URLs found in CSV")
            return
        
        logger.info(f"Starting to scrape {len(urls)} Medium articles...")
        
        # Scrape articles
        start_time = time.time()
        scraped_data, failed_urls = await scrape_articles(urls)
        end_time = time.time()
        
        # Report statistics
        success_count = len(scraped_data)
        fail_count = len(failed_urls)
        total_count = success_count + fail_count
        success_rate = (success_count / total_count) * 100 if total_count > 0 else 0
        
        logger.info(f"Scraping completed in {end_time - start_time:.2f} seconds")
        logger.info(f"Success rate: {success_rate:.2f}% ({success_count}/{total_count})")
        
        # Save successful scrapes
        if scraped_data:
            df = pd.DataFrame(scraped_data)
            output_csv = "medium_scraped_data.csv"
            df.to_csv(output_csv, index=False, encoding="utf-8")
            files.download(output_csv)
            logger.info(f"Successfully scraped {len(scraped_data)} articles. Results saved to {output_csv}")
        else:
            logger.warning("No articles were successfully scraped")
        
        # Save failed URLs
        if failed_urls:
            failed_csv = "failed_urls.csv"
            pd.DataFrame({'failed_urls': failed_urls}).to_csv(failed_csv, index=False, encoding="utf-8")
            files.download(failed_csv)
            logger.info(f"Saved {len(failed_urls)} failed URLs to {failed_csv}. Try scraping them later.")
        
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")

# Run the scraper
await main()