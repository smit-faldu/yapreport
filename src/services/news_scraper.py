import feedparser
import requests
from bs4 import BeautifulSoup
from src.models.schemas import GraphState
from src.services.supabase_uploader import get_covered_urls, get_covered_titles

def fetch_news(state: GraphState) -> dict:
    print("📰 Fetching global headlines...")
    
    # NEW: Fetch already covered URLs
    covered_urls = get_covered_urls()
    covered_titles_list = get_covered_titles() 
    past_topics_str = "\n".join([f"- {title}" for title in covered_titles_list]) if covered_titles_list else "None"
    if covered_urls:
        print(f"🛡️  Found {len(covered_urls)} previously covered articles. Filtering them out...")

    feeds = {
        "Geopolitics (BBC)":          "http://feeds.bbci.co.uk/news/world/rss.xml",
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
            
            valid_entries_count = 0
            source_news = f"--- {source.upper()} ---\n"
            
            for entry in parsed.entries[:15]: # Look at top 15 to ensure we get enough fresh ones
                title   = entry.get("title",   "No Title")
                link    = entry.get("link",    "No URL")
                summary = entry.get("summary", "No Summary").split("<")[0].strip()
                
                # NEW: Skip if we already covered it!
                if link in covered_urls:
                    continue
                    
                source_news += f"Title: {title}\nURL: {link}\nSummary: {summary}\n\n"
                valid_entries_count += 1
                
                if valid_entries_count >= 10: # Only keep 10 fresh ones per category
                    break
            
            if valid_entries_count > 0:
                all_news += source_news
                
        except Exception as e:
            print(f"  ❌ Failed {source}: {e}")

    print("\n--- FRESH RAW NEWS ---")
    print(all_news)
    print("------------------\n")
    return {"raw_news": all_news}

def scrape_news_page(state: GraphState) -> dict:
    url = state.get("target_url", "")
    print(f"🕸️ Scraping Webpage: {url}")

    if not url or url == "No URL":
        return {"scraped_text": "No additional details scraped."}

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        
        # Raise an exception if the response was an HTTP error (e.g., 404, 500)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # --- NEW LOGIC: Target the <article> tag ---
        article = soup.find('article')
        
        if article:
            # If the <article> tag exists, only grab paragraphs inside it
            paragraphs = article.find_all('p')
        else:
            # FALLBACK: If there's no <article> tag (e.g., live blog pages), grab all <p> tags
            print("⚠️ No <article> tag found. Falling back to page-wide paragraphs.")
            paragraphs = soup.find_all('p')
        # -------------------------------------------

        text = "\n".join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])

        scraped_text = text[:4000]
        print(f"✅ Scraped {len(scraped_text)} characters.")

        return {"scraped_text": scraped_text}
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Network/HTTP error during scraping: {e}")
        return {"scraped_text": "Failed to scrape full story. Relying on summary."}
    except Exception as e:
        print(f"❌ Scraping failed: {e}")
        return {"scraped_text": "Failed to scrape full story. Relying on summary."}