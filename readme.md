# Medium Articles Scraper and Search API

This project consists of two main components: a web scraper for Medium articles and a Flask API that allows searching through the scraped data.

## Overview

The project is designed to:
1. Scrape up to 500 Medium articles from a list of URLs
2. Extract key information including titles, subtitles, content, author info, claps, reading time, and images
3. Store the data in a CSV file
4. Provide a web API for searching through the collected articles

## Requirements

- Python 3.6+
- Required packages (included in requirements.txt):
  - requests
  - beautifulsoup4
  - pandas
  - flask
  - tqdm

## Project Structure

```
api/
├── medium_api.py           # Flask API application
├── medium_articles.csv     # CSV file containing scraped articles
├── requirements.txt        # Python dependencies
└── templates/              # HTML templates for the web interface
    └── index.html          # Homepage template
```

## Part A: Web Scraping

The web scraping component:
- Reads a list of Medium article URLs from a text file
- Visits each URL and extracts relevant information
- Saves the collected data to a CSV file (`medium_articles.csv`)

### Data Structure

The CSV file contains the following columns:
- `url`: The article URL
- `title`: Article title
- `subtitle`: Article subtitle (if available)
- `content`: Full article text content
- `author`: Author name
- `author_url`: Link to the author's profile
- `claps`: Number of claps the article received
- `reading_time`: Estimated reading time
- `images`: Pipe-separated list of image URLs in the article

## Part B: Flask API

The `medium_api.py` script creates a web API that allows searching through the scraped articles.

### API Endpoints

- **/** - Home page with basic instructions and a search interface
- **/search?keyword=KEYWORD** - Search for articles with KEYWORD in the title

### How to Use

The API is currently deployed on PythonAnywhere. You can access it at:
[https://hamzamalik22.pythonanywhere.com/]

To search for articles, use the web interface or make a direct API request:
```
[https://hamzamalik22.pythonanywhere.com/]/search?keyword=python
```

This will return articles with "python" in their title in JSON format.

## Deployment Details

### PythonAnywhere Deployment

This project is deployed on PythonAnywhere, a cloud platform designed for hosting Python applications.

#### Accessing the Deployment

- **Web Interface**: [https://hamzamalik22.pythonanywhere.com/]
- **API Endpoint**: [https://hamzamalik22.pythonanywhere.com/]/search?keyword=KEYWORD

#### Deployment Structure

The deployment on PythonAnywhere follows the structure shown in the "Project Structure" section above. The Flask application (`medium_api.py`) serves both the HTML interface and the JSON API endpoints.

## Notes

- Medium may rate-limit aggressive scraping; the script includes random delays to mitigate this
- With 500 articles including full content, the CSV file might become quite large
- Consider implementing more advanced features like authentication, enhanced search capabilities, or additional search parameters

## Troubleshooting

- If search results are unexpected, verify that the `medium_articles.csv` file contains the expected data
- For issues with the API, check the PythonAnywhere error logs
- Ensure all required dependencies are installed on the PythonAnywhere environment

## Contributors
