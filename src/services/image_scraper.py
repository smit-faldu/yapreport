import os
import requests
import time
from ddgs import DDGS
from PIL import Image, UnidentifiedImageError
from io import BytesIO

def download_images_for_script(script, output_dir="assets/temp_images"):
    os.makedirs(output_dir, exist_ok=True)
    downloaded_paths = []

    print("🖼️  Fetching B-Roll images from DuckDuckGo...")
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    for i, line in enumerate(script.dialogue):
        if not line.image_query or str(line.image_query).strip().lower() in ['none', 'null', 'na', 'n/a', '']:
            downloaded_paths.append(None)
            continue
            
        print(f"  🔍 Searching: {line.image_query}")
        try:
            # Anti-ban delay
            time.sleep(2.5)
            # Fetch up to 3 results
            results = list(DDGS().images(line.image_query, max_results=3, color="color"))
            
            if not results:
                print(f"  ❌ No image found for {line.image_query}")
                downloaded_paths.append(None)
                continue
                
            img_saved = False
            
            # Fallback loop: try each image result until one successfully loads
            for result in results:
                image_url = result.get('image')
                if not image_url: continue
                
                try:
                    response = requests.get(image_url, headers=headers, timeout=5)
                    # Raise an error if we get a 404 or 403 HTML page instead of an image
                    response.raise_for_status() 
                    
                    # Try to open the image. If it's corrupted or HTML, this raises UnidentifiedImageError
                    img = Image.open(BytesIO(response.content))
                    
                    # Ensure standard RGB format
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                        
                    max_width = 800
                    if img.width > max_width:
                        ratio = max_width / img.width
                        img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)
                        
                    save_path = os.path.join(output_dir, f"line_{i}.jpg")
                    img.save(save_path, "JPEG", quality=85)
                    
                    downloaded_paths.append(save_path)
                    print(f"  ✅ Saved {save_path}")
                    
                    img_saved = True
                    break  # Success! Break out of the fallback loop
                    
                except (requests.exceptions.RequestException, UnidentifiedImageError, OSError) as e:
                    print(f"    ⚠️ Bad image link, trying fallback... ({type(e).__name__})")
                    continue  # The image was bad, try the next URL in the results list
            
            # If all 3 links failed
            if not img_saved:
                print(f"  ❌ All 3 image links failed for '{line.image_query}'")
                downloaded_paths.append(None)
                
        except Exception as e:
            print(f"  ❌ Search failed for '{line.image_query}': {e}")
            downloaded_paths.append(None)
            
    return downloaded_paths