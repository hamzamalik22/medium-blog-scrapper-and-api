import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import csv
from tqdm import tqdm
import re
import os

# Headers to mimic a browser visit
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

def clean_url(url):
    """Ensure URL has 'https://' and is properly formatted."""
    url = url.strip()
    if not url.startswith("http"):
        url = "https://" + url
    return url

def read_urls_from_file(file_path):
    """Read and clean URLs from a file."""
    urls = []
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            line = line.strip()
            if line and not line.startswith("url"):
                urls.append(clean_url(line))
    return urls[:20]  # Process only first 20 URLs

def scrape_medium_article(url):
    """Scrape data from a Medium article."""
    try:
        time.sleep(random.uniform(1, 3))  # Add delay to avoid blocks
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"Skipping {url}, status code: {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract title
        title_elem = soup.find('h1')
        title = title_elem.get_text(strip=True) if title_elem else "No title found"

        # Extract subtitle
        subtitle_elem = soup.find('h2')
        subtitle = subtitle_elem.get_text(strip=True) if subtitle_elem else ""

        # Extract content
        article_elements = soup.find_all(['p', 'h2', 'h3', 'blockquote'])
        article_content = ' '.join(elem.get_text(strip=True) for elem in article_elements)

        # Extract author name
        author_elem = soup.find('meta', {'name': 'author'})
        author = author_elem['content'].strip() if author_elem else "Unknown"

        # Extract author URL (improved method)
        author_url = ""
        author_link_elem = soup.select_one('a[href*="/@"]')
        if author_link_elem:
            author_url = author_link_elem.get('href')
            if author_url and not author_url.startswith('http'):
                author_url = f"https://medium.com{author_url}"

        # Extract claps count
        claps = "0"
        claps_script = soup.find('script', string=re.compile(r'"clapCount":\d+'))
        if claps_script:
            claps_match = re.search(r'"clapCount":(\d+)', claps_script.string)
            if claps_match:
                claps = claps_match.group(1)

        # Extract reading time
        reading_time_elem = soup.find(string=re.compile(r'\d+ min read'))
        reading_time = reading_time_elem.strip() if reading_time_elem else "Unknown"

        # Extract image sources
        image_elements = soup.find_all('img')
        image_sources = [img.get('src') for img in image_elements if img.get('src') and not img.get('src').startswith('data:')]
        images = '|'.join(image_sources)

        return {
            'url': url,
            'title': title,
            'subtitle': subtitle,
            'content': article_content,
            'author': author,
            'author_url': author_url,
            'claps': claps,
            'reading_time': reading_time,
            'images': images
        }

    except Exception as e:
        print(f"Error scraping {url}: {str(e)}")
        return None

def main():
    url_file_path = 'url_technology.csv'
    selected_urls = read_urls_from_file(url_file_path)
    print(f"Selected {len(selected_urls)} URLs for scraping")

    scraped_data = []
    
    for url in tqdm(selected_urls, desc="Scraping Medium articles"):
        article_data = scrape_medium_article(url)
        if article_data:
            scraped_data.append(article_data)

    print(f"Successfully scraped {len(scraped_data)} articles")

    csv_file_path = 'medium_scraped_data.csv'
    
    csv_headers = [
        'url', 'title', 'subtitle', 'content', 'author',
        'author_url', 'claps', 'reading_time', 'images'
    ]
    
    with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=csv_headers)
        writer.writeheader()
        writer.writerows(scraped_data)
    
    print(f"Data saved to {csv_file_path}")

if __name__ == "__main__":
    main()
