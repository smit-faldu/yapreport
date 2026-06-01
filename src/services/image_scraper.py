import os
import requests
from duckduckgo_search import DDGS
from PIL import Image
from io import BytesIO

def download_images_for_script(script, output_dir="assets/temp_images"):
    os.makedirs(output_dir, exist_ok=True)
    downloaded_paths = []

    print("🖼️  Fetching B-Roll images from DuckDuckGo...")
    
    for i, line in enumerate(script.dialogue):
        if not line.image_query or str(line.image_query).strip().lower() in ['none', 'null', 'na', 'n/a', '']:
            downloaded_paths.append(None)
            continue
            
        print(f"  🔍 Searching: {line.image_query}")
        try:
            # Search DDG
            results = DDGS().images(line.image_query, max_results=3)
            if not results:
                print(f"  ❌ No image found for {line.image_query}")
                downloaded_paths.append(None)
                continue
                
            # Download the first result
            image_url = results[0]['image']
            response = requests.get(image_url, timeout=5)
            
            # Load with Pillow to standardize format and prevent FFmpeg crashes
            img = Image.open(BytesIO(response.content))
            if img.mode != 'RGB':
                img = img.convert('RGB')
                
            # Resize it down to max 800 width so it doesn't take up the whole vertical screen
            max_width = 800
            if img.width > max_width:
                ratio = max_width / img.width
                img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)
                
            save_path = os.path.join(output_dir, f"line_{i}.jpg")
            img.save(save_path, "JPEG", quality=85)
            downloaded_paths.append(save_path)
            print(f"  ✅ Saved {save_path}")
            
        except Exception as e:
            print(f"  ❌ Failed to process image for '{line.image_query}': {e}")
            downloaded_paths.append(None)
            
    return downloaded_paths