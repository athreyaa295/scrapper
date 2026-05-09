import sys
import os
import json
from scraper import scrape_events

def main():
    print("Starting GitHub Actions Scraping Job...")
    
    # Run the scraper
    try:
        events = scrape_events()
    except Exception as e:
        print(f"Error during scraping: {e}")
        sys.exit(1)
        
    print(f"Scraped {len(events)} events.")
    
    # Convert events to JSON serializable list
    safe_events = []
    for e in events:
        if hasattr(e, 'model_dump'):
            safe_events.append(e.model_dump())
        elif hasattr(e, 'dict'):
            safe_events.append(e.dict())
        else:
            safe_events.append(e)
            
    # Save to data/jobs.json
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(root_dir, 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    output_path = os.path.join(data_dir, 'jobs.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(safe_events, f, indent=2, ensure_ascii=False)
        
    print(f"Successfully saved {len(safe_events)} events to {output_path}")

if __name__ == "__main__":
    main()
