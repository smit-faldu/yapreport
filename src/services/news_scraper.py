import feedparser
import requests
from bs4 import BeautifulSoup
from src.models.schemas import GraphState

def fetch_news(state: GraphState) -> dict:
    print("📰 Fetching global headlines...")

    feeds = {
        "Geopolitics (BBC)":          "http://feeds.bbci.co.uk/news/world/rss.xml",
        "Finance (Yahoo)":            "https://finance.yahoo.com/news/rss",
        "Tech (BBC)":                 "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "Science & Environment(BBC)": "http://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
        "Health (BBC)":               "https://feeds.bbci.co.uk/news/health/rss.xml",
        "business (BBC)":             "https://feeds.bbci.co.uk/news/business/rss.xml",
        "politics (BBC)":             "https://feeds.bbci.co.uk/news/politics/rss.xml",
    }

    all_news = ""
    for source, url in feeds.items():
        try:
            parsed = feedparser.parse(url)
            if parsed.get("status", 0) not in [200, 301, 302]:
                continue
            all_news += f"--- {source.upper()} ---\n"
            for entry in parsed.entries[:10]:
                title   = entry.get("title",   "No Title")
                link    = entry.get("link",    "No URL")
                summary = entry.get("summary", "No Summary").split("<")[0].strip()
                all_news += f"Title: {title}\nURL: {link}\nSummary: {summary}\n\n"
        except Exception as e:
            print(f"  ❌ Failed {source}: {e}")

    print("\n--- RAW NEWS ---")
    print(all_news)
    print("------------------\n")
    return {"raw_news": all_news}

def scrape_news_page(state: GraphState) -> dict:
    url = state.get("target_url", "")
    print(f"🕸️ Scraping Webpage: {url}")

    if not url or url == "No URL":
        return {"scraped_text": "No additional details scraped."}

    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        response = requests.get(url, headers=headers, timeout=10)

        soup = BeautifulSoup(response.text, 'html.parser')

        paragraphs = soup.find_all('p')
        text = "\n".join([p.get_text() for p in paragraphs])

        scraped_text = text[:4000]
        print(f"✅ Scraped {len(scraped_text)} characters.")

        return {"scraped_text": scraped_text}
    except Exception as e:
        print(f"❌ Scraping failed: {e}")
        return {"scraped_text": "Failed to scrape full story. Relying on summary."}
