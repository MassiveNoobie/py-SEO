import csv
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.common.exceptions import TimeoutException, WebDriverException
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import os

# Log loaded websites
def log(param):
    pass

# Firefox WebDriver setup
options = webdriver.FirefoxOptions()
options.add_argument('headless')
service = Service('C:/Users/ityle/Documents/reddit streams/geckodriver.exe')
browser = webdriver.Firefox(service=service, options=options)

websites_csv_file = 'websites.csv'  # Path to your CSV file
websites = []

if os.path.exists(websites_csv_file):
    with open(websites_csv_file, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)  # Automatically captures all columns as keys
        for row in reader:
            # Convert the entire row to a dictionary, dynamically capturing all columns
            websites.append(row)
else:
    log(f"CSV file {websites_csv_file} not found.")
    raise FileNotFoundError(f"{websites_csv_file} does not exist. Please provide a valid CSV file.")





log(f"Loaded {len(websites)} websites from {websites_csv_file}.")


print('test')
# Expanded language detection using common words across 40 languages
language_keywords = {
    'en': ["the", "and", "of", "to", "in", "it", "is"],
    'ru': ["и", "в", "не", "на", "он", "с", "что"],
    'es': ["el", "la", "de", "y", "que", "en", "es"],
    'fr': ["le", "la", "de", "et", "que", "en", "il"],
    'zh': ["的", "一", "是", "不", "了", "人", "我"],
    'ja': ["の", "に", "は", "を", "が", "です", "で"],
    'hi': ["और", "को", "है", "के", "यह", "से", "कि"],
    'ar': ["ال", "من", "في", "على", "و", "مع", "كان"],
   # 'pt': ["o", "a", "e", "de", "do", "em", "que"],
    'de': ["der", "die", "und", "in", "den", "von", "zu"],
    'it': ["il", "la", "e", "di", "che", "in", "a"],
    'nl': ["de", "het", "en", "van", "in", "een", "is"]
}

# In-memory logging and results storage
log_data = []
results = []

# Load previously processed websites
processed_websites = set()
if os.path.exists('website_analysis.csv'):
    with open('website_analysis.csv', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            processed_websites.add(row['url'])

def log(message):
    log_data.append(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}")
    with open('scraper_log.txt', 'a', encoding='utf-8') as logfile:
        logfile.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")

def detect_language(text, title):
    scores = {lang: sum(text.lower().count(word) + title.lower().count(word) for word in words)
              for lang, words in language_keywords.items()}
    return max(scores, key=scores.get)

def score_website(data):
    score = 0
    if data.get('language') != 'en': score += 1
    if data.get('word_count', 0) < 100: score += 2
    if data.get('internal_links', 0) < 3: score += 1
    if data.get('advertisements', 0) > 3: score += 2
    if data.get('error_code') is not None: score += 2
    if data.get('redirect_count', 0) > 3: score += 2
    if data.get('h1_count', 0) > 5 or data.get('h2_count', 0) > 10 or data.get('h3_count', 0) > 15: score += 2
    return score

def classify_spam(score):
    if score <= 2:
        return 'Not Spammy'
    elif score <= 4:
        return 'Moderately Spammy'
    else:
        return 'Highly Spammy'

fieldnames = ['url', 'last_crawled', 'webscrape_at', 'language', 'word_count', 'code_count', 'internal_links', 'advertisements',
              'spam_score', 'spam_classification', 'status', 'error_code', 'favicon', 'twitter',
              'instagram', 'youtube', 'h1_count', 'h2_count', 'h3_count', 'redirect_count',
              'redirect_chain', 'page_title', 'page_description', 'top_words',
              'lang_score_en', 'lang_score_ru', 'lang_score_es', 'lang_score_fr',
              'lang_score_zh', 'lang_score_ja', 'lang_score_hi', 'lang_score_ar',
              'lang_score_de', 'lang_score_it', 'lang_score_nl']


with open('website_analysis.csv', 'a', newline='', encoding='utf-8') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    if os.stat('website_analysis.csv').st_size == 0:
        writer.writeheader()



    def sanitize_text(text):
        if isinstance(text, str):
            return ' '.join(text.split())  # Replaces all whitespace (including newlines) with single spaces
        return text


    def scrape_website(site_data):
        # Dynamically extract the URL and any other fields from the row dictionary
        url = site_data.get('url')  # Assumes 'url' is always a column in the CSV
        last_crawled = site_data.get('last_crawled')  # Optional: only if it exists

        if not url:
            log("Skipping row with missing URL.")
            return

        if url in processed_websites:
            log(f"Skipping already processed {url}")
            return

        error_code = None
        redirect_count = 0
        redirect_chain = [url]
        try:
            log(f"Accessing {url}")
            browser.set_page_load_timeout(10)
            browser.get(f"{url}")
            final_url = browser.current_url

            # Check for redirects
            while final_url != url and redirect_count < 10:
                redirect_chain.append(final_url)
                url = final_url
                browser.get(final_url)
                final_url = browser.current_url
                redirect_count += 1

            # Capture title and content for language detection
            soup = BeautifulSoup(browser.page_source, 'html.parser')
            page_title = soup.title.string if soup.title else ''
            page_description = soup.find('meta', attrs={'name': 'description'})
            page_description = page_description['content'] if page_description else ''
            body_text = soup.body.get_text() if soup.body else ''
            language = detect_language(body_text, page_title)
            word_count = len(body_text.split())
            # Get all text content and split into words
            words = body_text.lower().split()
            word_freq = {}
            for word in words:
                if len(word) > 2:  # Skip very short words
                    word_freq[word] = word_freq.get(word, 0) + 1
            top_words = ', '.join([word for word, count in
                                   sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:300]])

            # Calculate language scores
            lang_scores = {}
            combined_text = f"{page_title} {page_description} {top_words}"
            for lang, keywords in language_keywords.items():
                score = sum(combined_text.lower().count(word) for word in keywords)
                lang_scores[f'lang_score_{lang}'] = score
            # Other metrics
            code_count = len(soup.find_all(['script', 'style']))
            internal_links = len(soup.find_all('a', href=True))
            advertisements = len(soup.find_all(lambda tag: tag.name == 'div' and 'ad' in tag.get('class', [])))



            # Count headers for analysis
            h1_count = len(soup.find_all('h1'))
            h2_count = len(soup.find_all('h2'))
            h3_count = len(soup.find_all('h3'))

            data = {
                'url': url,
                'last_crawled': last_crawled,  # Keep the existing "Last Crawled" value
                'webscrape_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'language': language,
                'word_count': word_count,
                'h1_count': h1_count,
                'h2_count': h2_count,
                'h3_count': h3_count,
                'code_count': code_count,
                'internal_links': internal_links,
                'advertisements': advertisements,
                'redirect_count': redirect_count,
                'redirect_chain': ', '.join(redirect_chain),
                'status': 'success',
                'page_title': page_title,
                'page_description': page_description,
                'top_words': top_words,
                ** lang_scores  # Add all language scores to data
            }

            data['spam_score'] = score_website(data)
            data['spam_classification'] = classify_spam(data['spam_score'])
            writer.writerow(data)
            csvfile.flush()
            processed_websites.add(url)

        except Exception as e:
            log(f"Error processing {url}: {e}")

    for site in websites:
        scrape_website(site)

browser.quit()
log("Scraping complete.")
