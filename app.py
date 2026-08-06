#!/usr/bin/env python3
"""
Daf Yomi Web Application
Flask web server for downloading and combining Daf Yomi pages
"""

from flask import Flask, render_template, request, jsonify, send_file, Response
from curl_cffi import requests
import os
import re
import tempfile
import zipfile
from pathlib import Path
from bs4 import BeautifulSoup
from datetime import datetime
import json
import time
import uuid
from threading import Thread

app = Flask(__name__)

# Global dictionary to store progress data
progress_data = {}

# Hebrew number mappings
HEBREW_NUMBERS = {
    'ב': 2, 'ג': 3, 'ד': 4, 'ה': 5, 'ו': 6, 'ז': 7, 'ח': 8, 'ט': 9, 'י': 10,
    'יא': 11, 'יב': 12, 'יג': 13, 'יד': 14, 'טו': 15, 'טז': 16, 'יז': 17, 'יח': 18, 'יט': 19, 'כ': 20,
    'כא': 21, 'כב': 22, 'כג': 23, 'כד': 24, 'כה': 25, 'כו': 26, 'כז': 27, 'כח': 28, 'כט': 29, 'ל': 30,
    'לא': 31, 'לב': 32, 'לג': 33, 'לד': 34, 'לה': 35, 'לו': 36, 'לז': 37, 'לח': 38, 'לט': 39, 'מ': 40,
    'מא': 41, 'מב': 42, 'מג': 43, 'מד': 44, 'מה': 45, 'מו': 46, 'מז': 47, 'מח': 48, 'מט': 49, 'נ': 50,
    'נא': 51, 'נב': 52, 'נג': 53, 'נד': 54, 'נה': 55, 'נו': 56, 'נז': 57, 'נח': 58, 'נט': 59, 'ס': 60,
    'סא': 61, 'סב': 62, 'סג': 63, 'סד': 64, 'סה': 65, 'סו': 66, 'סז': 67, 'סח': 68, 'סט': 69, 'ע': 70,
    'עא': 71, 'עב': 72, 'עג': 73, 'עד': 74, 'עה': 75, 'עו': 76, 'עז': 77, 'עח': 78, 'עט': 79, 'פ': 80,
    'פא': 81, 'פב': 82, 'פג': 83, 'פד': 84, 'פה': 85, 'פו': 86, 'פז': 87, 'פח': 88, 'פט': 89, 'צ': 90,
    'צא': 91, 'צב': 92, 'צג': 93, 'צד': 94, 'צה': 95, 'צו': 96, 'צז': 97, 'צח': 98, 'צט': 99, 'ק': 100,
    'קא': 101, 'קב': 102, 'קג': 103, 'קד': 104, 'קה': 105, 'קו': 106, 'קז': 107, 'קח': 108, 'קט': 109, 'קי': 110,
    'קיא': 111, 'קיב': 112, 'קיג': 113, 'קיד': 114, 'קטו': 115, 'קטז': 116, 'קיז': 117, 'קיח': 118, 'קיט': 119, 'קכ': 120,
    'קכא': 121, 'קכב': 122, 'קכג': 123, 'קכד': 124, 'קכה': 125, 'קכו': 126, 'קכז': 127, 'קכח': 128, 'קכט': 129, 'קל': 130,
    'קלא': 131, 'קלב': 132, 'קלג': 133, 'קלד': 134, 'קלה': 135, 'קלו': 136, 'קלז': 137, 'קלח': 138, 'קלט': 139, 'קמ': 140,
    'קמא': 141, 'קמב': 142, 'קמג': 143, 'קמד': 144, 'קמה': 145, 'קמו': 146, 'קמז': 147, 'קמח': 148, 'קמט': 149, 'קנ': 150,
    'קנא': 151, 'קנב': 152, 'קנג': 153, 'קנד': 154, 'קנה': 155, 'קנו': 156, 'קנז': 157, 'קנח': 158, 'קנט': 159, 'קס': 160,
    'קסא': 161, 'קסב': 162, 'קסג': 163, 'קסד': 164, 'קסה': 165, 'קסו': 166, 'קסז': 167, 'קסח': 168, 'קסט': 169, 'קע': 170,
    'קעא': 171, 'קעב': 172, 'קעג': 173, 'קעד': 174, 'קעה': 175, 'קעו': 176,
}

# Reverse mapping for converting numbers back to Hebrew
NUMBER_TO_HEBREW = {v: k for k, v in HEBREW_NUMBERS.items()}

# Hebrew to English tractate name mapping
TRACTATE_TRANSLITERATIONS = {
    'ברכות': 'berakhot',
    'שבת': 'shabbat',
    'עירובין': 'eruvin',
    'פסחים': 'pesachim',
    'שקלים': 'shekalim',
    'יומא': 'yoma',
    'סוכה': 'sukkah',
    'ביצה': 'beitzah',
    'ראש השנה': 'rosh_hashanah',
    'תענית': 'taanit',
    'מגילה': 'megillah',
    'מועד קטן': 'moed_katan',
    'חגיגה': 'chagigah',
    'יבמות': 'yevamot',
    'כתובות': 'ketubot',
    'נדרים': 'nedarim',
    'נזיר': 'nazir',
    'סוטה': 'sotah',
    'גיטין': 'gittin',
    'קידושין': 'kiddushin',
    'בבא קמא': 'bava_kamma',
    'בבא מציעא': 'bava_metzia',
    'בבא בתרא': 'bava_batra',
    'סנהדרין': 'sanhedrin',
    'מכות': 'makkot',
    'שבועות': 'shevuot',
    'עבודה זרה': 'avodah_zarah',
    'הוריות': 'horayot',
    'זבחים': 'zevachim',
    'מנחות': 'menachot',
    'חולין': 'chullin',
    'בכורות': 'bekhorot',
    'ערכין': 'arakhin',
    'תמורה': 'temurah',
    'כריתות': 'keritot',
    'מעילה': 'meilah',
    'תמיד': 'tamid',
    'מדות': 'middot',
    'קינים': 'kinnim',
    'נדה': 'niddah'
}

# All tractates - CORRECTED numbers from daf-yomi.com 
TRACTATES = {
    'ברכות': 283,        # Verified: 283, not 301
    'שבת': 284,          # Following sequence pattern  
    'עירובין': 285,      # Following sequence pattern
    'פסחים': 286,        # Following sequence pattern
    'שקלים': 287,        # Following sequence pattern
    'יומא': 288,         # Following sequence pattern (was working by coincidence)
    'סוכה': 289,         # Following sequence pattern
    'ביצה': 290,         # Verified: 290, not 308
    'ראש השנה': 291,     # Following sequence pattern
    'תענית': 292,        # Following sequence pattern
    'מגילה': 293,       # Following sequence pattern
    'מועד קטן': 294,     # Following sequence pattern
    'חגיגה': 295,       # Following sequence pattern
    'יבמות': 296,       # Following sequence pattern
    'כתובות': 297,      # Following sequence pattern
    'נדרים': 298,       # Following sequence pattern
    'נזיר': 299,         # Following sequence pattern
    'סוטה': 300,         # Following sequence pattern
    'גיטין': 301,        # Following sequence pattern
    'קידושין': 302,      # Following sequence pattern
    'בבא קמא': 303,      # Following sequence pattern
    'בבא מציעא': 304,    # Following sequence pattern
    'בבא בתרא': 305,     # Following sequence pattern
    'סנהדרין': 306,      # Following sequence pattern
    'מכות': 307,         # Following sequence pattern
    'שבועות': 308,       # Following sequence pattern (this is what you got when selecting ביצה!)
    'עבודה זרה': 309,    # We have local files (סב-עו) as fallback
    'הוריות': 310,       # We have local files (ה-י) as fallback
    'זבחים': 311,        # We have local files (ב-ה) as fallback
    'מנחות': 312,        # Following sequence pattern
    'חולין': 313,         # Following sequence pattern
    'בכורות': 314,        # Following sequence pattern
    'ערכין': 315,         # Following sequence pattern
    'תמורה': 316,         # Following sequence pattern
    'כריתות': 317,        # Following sequence pattern
    'מעילה': 318,         # Following sequence pattern
    'תמיד': 319,          # Following sequence pattern
    'מדות': 320,          # Following sequence pattern
    'קינים': 321,         # Following sequence pattern (was קנים on site)
    'נדה': 322            # Following sequence pattern (was נידה on site)
}

def hebrew_to_amud_number(daf_hebrew, amud):
    """Convert Hebrew daf notation to amud number used by the site"""
    page_num = HEBREW_NUMBERS.get(daf_hebrew, 0)
    if page_num == 0:
        return 0
    
    if amud == 'א':
        return (page_num - 1) * 2 + 1
    else:  # ב
        return (page_num - 1) * 2 + 2

def create_informative_filename(tractate_name, start_daf, start_amud, end_daf, end_amud):
    """
    Create informative filename following pattern:
    עבודה זרה דף עא עמוד א - דף עו עמוד ב -> avodah_zarah_71-76.html
    """
    # Get English transliteration
    english_name = TRACTATE_TRANSLITERATIONS.get(tractate_name, tractate_name.replace(' ', '_'))
    
    # Convert Hebrew numbers to Arabic numbers
    start_num = HEBREW_NUMBERS.get(start_daf, 0)
    end_num = HEBREW_NUMBERS.get(end_daf, 0)
    
    # Convert Hebrew amud to English
    amud_map = {'א': 'a', 'ב': 'b'}
    start_amud_en = amud_map.get(start_amud, start_amud.lower())
    end_amud_en = amud_map.get(end_amud, end_amud.lower())
    
    # Handle single page case
    if start_num == end_num and start_amud == end_amud:
        return f"{english_name}_{start_num}{start_amud_en}.html"
    
    # Handle same daf, different amud
    if start_num == end_num:
        return f"{english_name}_{start_num}{start_amud_en}-{end_amud_en}.html"
    
    # Handle different dafim - use page range
    return f"{english_name}_{start_num}-{end_num}.html"

def download_daf_page(massechet_num, amud_num):
    """Download a single daf page using curl_cffi with browser impersonation"""
    url = f"https://daf-yomi.com/Dafyomi_Page.aspx?vt=5&massechet={massechet_num}&amud={amud_num}&fs=0"

    try:
        print(f"Attempting real download: {url}")
        # Add small delay to be respectful
        time.sleep(0.2)

        # Use curl_cffi with Chrome 120 impersonation (bypasses Cloudflare)
        response = requests.get(url, impersonate='chrome120', timeout=30)
        response.raise_for_status()
        print(f"SUCCESS: Downloaded {len(response.text)} characters from real site")
        return response.text
    except Exception as e:
        print(f"Real download failed: {e}")

        # Try local files as fallback for tractates we have
        local_content = try_load_existing_page(massechet_num, amud_num)
        if local_content:
            print(f"Using local file as fallback")
            return local_content

        print(f"No local fallback available")
        return None

def try_load_existing_page(massechet_num, amud_num):
    """Try to load an existing downloaded page from the pages/ directory"""
    print(f"DEBUG: Looking for massechet_num={massechet_num}, amud_num={amud_num}")
    
    # Convert massechet number to name
    massechet_names = {v: k for k, v in TRACTATES.items()}
    massechet_name = massechet_names.get(massechet_num, "")
    print(f"DEBUG: massechet_name = '{massechet_name}'")
    
    if not massechet_name:
        print(f"DEBUG: No massechet name found for ID {massechet_num}")
        return None
        
    # Convert amud number back to daf and side
    # amud_num = (page_num - 1) * 2 + 1 for א, (page_num - 1) * 2 + 2 for ב
    # So: page_num = (amud_num + 1) // 2 for א, (amud_num) // 2 + 1 for ב
    if amud_num % 2 == 1:  # א
        daf_num = (amud_num + 1) // 2
        side = 'א'
    else:  # ב
        daf_num = amud_num // 2
        side = 'ב'
    
    daf_hebrew = NUMBER_TO_HEBREW.get(daf_num, str(daf_num))
    print(f"DEBUG: amud_num={amud_num} -> daf_num={daf_num} -> daf_hebrew='{daf_hebrew}' side='{side}'")
    
    # Try to find the file in pages/ directory
    import glob
    pages_dir = "pages"
    
    # Look for files matching the pattern
    possible_patterns = [
        f"{massechet_name} {daf_hebrew} ע{side}.html",
        f"{massechet_name} {daf_hebrew} ע\"{side}\".html", 
        f"{massechet_name}_{daf_hebrew}_ע{side}.html"
    ]
    
    print(f"DEBUG: Looking for patterns: {possible_patterns}")
    
    for pattern in possible_patterns:
        file_path = os.path.join(pages_dir, pattern)
        print(f"DEBUG: Checking {file_path}")
        if os.path.exists(file_path):
            print(f"Found existing file: {file_path}")
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
                continue
    
    print(f"No existing file found for {massechet_name} {daf_hebrew} ע{side}")
    
    # List what files are actually there
    if os.path.exists(pages_dir):
        actual_files = [f for f in os.listdir(pages_dir) if massechet_name in f and f.endswith('.html')]
        print(f"DEBUG: Actual files containing '{massechet_name}': {actual_files}")
    
    return None


def strip_kodat_widget(root):
    """Remove Kodat.co.il floating widget (scripts, host div, iframes) from a BeautifulSoup subtree."""
    if root is None:
        return
    kw = 'kodat'
    for tag in list(root.find_all(True)):
        if getattr(tag, 'attrs', None) is None:
            continue
        tag_id = tag.get('id') or ''
        if kw in tag_id.lower():
            tag.decompose()
            continue
        if any(kw in str(c).lower() for c in (tag.get('class') or [])):
            tag.decompose()
    for script in list(root.find_all('script')):
        src = (script.get('src') or '').lower()
        blob = (script.string or script.get_text() or '').lower()
        if kw in src or kw in blob:
            script.decompose()
    for iframe in list(root.find_all('iframe')):
        if kw in (iframe.get('src') or '').lower():
            iframe.decompose()


def extract_content_and_title(html_content):
    """Extract the Hebrew title and content - works with both raw and processed pages"""
    if not html_content:
        return None, None
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Extract Hebrew title - prefer the specific page title element from daf-yomi.com
    title_element = soup.find('h1', id='ContentPlaceHolderMain_hdrMassechet2')
    if not title_element:
        title_element = soup.find('h1')
    if title_element:
        title = title_element.get_text().strip()
    else:
        # Try title tag as fallback
        title_tag = soup.find('title')
        title = title_tag.get_text().strip() if title_tag else "Unknown"
    
    def finish(t, node):
        if node is not None:
            strip_kodat_widget(node)
        return t, node

    # For already processed files (from pages/ directory), just get the body content
    content_div = soup.find('div', class_='content')
    if content_div:
        print("DEBUG: Found .content div in processed file")
        return finish(title, content_div)
    
    # For raw files from daf-yomi.com, look for the clsContainer that wraps the Steinsaltz content
    # Structure: <div class="clsContainer"><h2>שטיינזלץ</h2><div class="clsBody">...</div></div>
    # Try to find the clsBody directly inside a clsContainer with a שטיינזלץ h2
    for container in soup.find_all('div', class_='clsContainer'):
        h2 = container.find('h2', string=lambda text: text and 'שטיינזלץ' in text)
        if h2:
            cls_body = container.find('div', class_='clsBody')
            if cls_body:
                print("DEBUG: Found שטיינזלץ clsBody in clsContainer")
                return finish(title, cls_body)

    # Fallback: look for ContentPlaceHolderMain_divTextWrapper
    text_wrapper = soup.find('div', id='ContentPlaceHolderMain_divTextWrapper')
    if text_wrapper:
        print("DEBUG: Found ContentPlaceHolderMain_divTextWrapper")
        return finish(title, text_wrapper)

    # Fallback: look for פירוש שטיינזלץ section (legacy format)
    steinsaltz_heading = soup.find('h2', string=lambda text: text and 'פירוש שטיינזלץ' in text)
    if steinsaltz_heading:
        print("DEBUG: Found פירוש שטיינזלץ section in raw file")
        steinsaltz_section = steinsaltz_heading.find_parent()
        if steinsaltz_section:
            content_div = steinsaltz_section.find('div')
            if content_div:
                steinsaltz_section = content_div
        
        # Clean up content
        if steinsaltz_section:
            for h1 in steinsaltz_section.find_all('h1'):
                h1.decompose()
            for h2 in steinsaltz_section.find_all('h2'):
                if 'פירוש שטיינזלץ' in h2.get_text():
                    h2.decompose()
        
        return finish(title, steinsaltz_section)
    
    # Fallback: for processed files, just get the body content minus the h1
    body = soup.find('body')
    if body:
        print("DEBUG: Using body content as fallback")
        # Create a copy and remove the h1 to avoid duplication
        body_copy = BeautifulSoup(str(body), 'html.parser')
        title_in_body = body_copy.find('h1')
        if title_in_body:
            title_in_body.decompose()
        return finish(title, body_copy)
    
    print("DEBUG: No content found")
    return title, None

def create_html_page(title, content):
    """Create a complete HTML page with the extracted content"""
    html_template = f"""<!DOCTYPE html>
<html dir="rtl" lang="he">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: 'Times New Roman', serif;
            direction: rtl;
            text-align: right;
            margin: 20px auto;
            max-width: 800px;
            line-height: 1.6;
        }}
        h1 {{
            color: #8B4513;
            border-bottom: 2px solid #8B4513;
            padding-bottom: 10px;
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <div class="content">
        {content}
    </div>
</body>
</html>"""
    return html_template

@app.route('/')
def index():
    """Main page with form for selecting tractate and pages"""
    return render_template('index.html', tractates=TRACTATES)

@app.route('/api/progress/<task_id>')
def progress_stream(task_id):
    """Server-Sent Events endpoint for progress updates"""
    def generate():
        while task_id in progress_data:
            data = progress_data[task_id]
            yield f"data: {json.dumps(data)}\n\n"
            
            if data.get('status') in ['completed', 'error']:
                # Clean up completed tasks after sending final update
                time.sleep(1)
                if task_id in progress_data:
                    del progress_data[task_id]
                break
                
            time.sleep(0.5)  # Update every 500ms
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/download-file/<task_id>')
def download_completed_file(task_id):
    """Download the completed file"""
    if task_id not in progress_data:
        return jsonify({'error': 'Task not found'}), 404
    
    data = progress_data[task_id]
    if data.get('status') != 'completed':
        return jsonify({'error': 'Task not completed'}), 400
    
    file_path = data.get('file_path')
    filename = data.get('filename')
    temp_dir = data.get('temp_dir')
    
    if not file_path or not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
    
    def cleanup_after_send():
        """Clean up temporary files after sending"""
        try:
            if temp_dir and os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir)
                print(f"DEBUG: Cleaned up temp dir: {temp_dir}")
        except Exception as e:
            print(f"ERROR: Failed to cleanup temp dir: {e}")
        
        # Remove from progress_data
        if task_id in progress_data:
            del progress_data[task_id]
    
    # Schedule cleanup after response is sent
    from threading import Timer
    Timer(2.0, cleanup_after_send).start()  # Clean up after 2 seconds
    
    return send_file(file_path, as_attachment=True, download_name=filename)

@app.route('/api/download', methods=['POST'])
def download_pages():
    """API endpoint to start download task and return task ID"""
    try:
        print(f"DEBUG: Received download request")
        data = request.json
        print(f"DEBUG: Request data: {data}")
        
        tractate_name = data.get('tractate')
        start_daf = data.get('start_daf')
        start_amud = data.get('start_amud')
        end_daf = data.get('end_daf')  
        end_amud = data.get('end_amud')
        
        print(f"DEBUG: tractate='{tractate_name}', start='{start_daf}{start_amud}', end='{end_daf}{end_amud}'")
        
        # Validate inputs
        if not all([tractate_name, start_daf, start_amud, end_daf, end_amud]):
            print(f"DEBUG: Missing parameters")
            return jsonify({'error': 'Missing required parameters'}), 400
            
        # Get tractate ID
        massechet_num = TRACTATES.get(tractate_name)
        print(f"DEBUG: Found massechet_num={massechet_num} for '{tractate_name}'")
        if not massechet_num:
            return jsonify({'error': f'Unknown tractate: {tractate_name}'}), 400
            
        # Validate Hebrew page numbers
        if start_daf not in HEBREW_NUMBERS or end_daf not in HEBREW_NUMBERS:
            return jsonify({'error': 'Invalid Hebrew page numbers'}), 400
            
        # Generate unique task ID
        task_id = str(uuid.uuid4())
        
        # Initialize progress data
        progress_data[task_id] = {
            'status': 'starting',
            'progress': 0,
            'current_page': '',
            'total_pages': 0,
            'completed_pages': 0,
            'message': 'מתחיל הורדה...'
        }
        
        # Start background download task
        thread = Thread(target=download_pages_background, args=(
            task_id, tractate_name, start_daf, start_amud, end_daf, end_amud, massechet_num
        ))
        thread.daemon = True
        thread.start()
        
        return jsonify({'task_id': task_id})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def download_pages_background(task_id, tractate_name, start_daf, start_amud, end_daf, end_amud, massechet_num):
    """Background task to download pages with progress updates"""
    try:
        # Calculate total number of pages to download
        start_num = HEBREW_NUMBERS[start_daf]
        end_num = HEBREW_NUMBERS[end_daf]
        
        total_pages = 0
        for daf_num in range(start_num, end_num + 1):
            for amud in ['א', 'ב']:
                # Skip if we're at start daf and before start amud
                if daf_num == start_num and start_amud == 'ב' and amud == 'א':
                    continue
                # Skip if we're at end daf and after end amud  
                if daf_num == end_num and end_amud == 'א' and amud == 'ב':
                    continue
                total_pages += 1
        
        # Update progress with total pages
        progress_data[task_id].update({
            'total_pages': total_pages,
            'status': 'downloading',
            'message': 'מוריד דפים...'
        })
            
        # Create a temporary file that persists until explicitly deleted
        temp_dir = tempfile.mkdtemp()
        pages = []
        completed_pages = 0
        
        # Download pages with progress updates
        for daf_num in range(start_num, end_num + 1):
            for amud in ['א', 'ב']:
                # Skip if we're at start daf and before start amud
                if daf_num == start_num and start_amud == 'ב' and amud == 'א':
                    continue
                # Skip if we're at end daf and after end amud  
                if daf_num == end_num and end_amud == 'א' and amud == 'ב':
                    continue
                    
                daf_hebrew = NUMBER_TO_HEBREW[daf_num]
                current_page = f"{daf_hebrew} ע{amud}"
                
                # Update progress
                progress_data[task_id].update({
                    'current_page': current_page,
                    'completed_pages': completed_pages,
                    'progress': int((completed_pages / total_pages) * 100),
                    'message': f'מוריד דף {current_page}...'
                })
                
                amud_number = hebrew_to_amud_number(daf_hebrew, amud)
                
                if amud_number == 0:
                    completed_pages += 1
                    continue
                    
                # Download the page
                print(f"DEBUG: Downloading {daf_hebrew} {amud} (amud_number={amud_number})")
                html_content = download_daf_page(massechet_num, amud_number)
                
                if html_content:
                    title, content = extract_content_and_title(html_content)
                    
                    if title and content:
                        complete_html = create_html_page(title, str(content))
                        pages.append({'title': title, 'content': complete_html})
                        print(f"DEBUG: Added page to list, total pages: {len(pages)}")
                    else:
                        print(f"DEBUG: Failed to extract title/content from page")
                else:
                    print(f"DEBUG: No html_content for {daf_hebrew} {amud}")
                
                completed_pages += 1
                
                # Update progress after each page
                progress_data[task_id].update({
                    'completed_pages': completed_pages,
                    'progress': int((completed_pages / total_pages) * 100)
                })
        
        print(f"DEBUG: Final pages count: {len(pages)}")
        if not pages:
            error_msg = f'Unable to download {tractate_name} pages. The daf-yomi.com site appears to be blocking automated requests (likely Cloudflare protection). This affects both the web app and manual scripts. You may need to: 1) Try from a different network, 2) Use a VPN, or 3) Wait for the site restrictions to be lifted.'
            progress_data[task_id].update({
                'status': 'error',
                'message': error_msg
            })
            return
            
        # Update progress - creating combined file
        progress_data[task_id].update({
            'status': 'processing',
            'progress': 100,
            'message': 'יוצר קובץ מאוחד...'
        })
            
        # Create combined HTML
        combined_html = create_combined_html(pages, tractate_name, start_daf, start_amud, end_daf, end_amud)
        
        # Save to temporary file with informative name
        filename = create_informative_filename(tractate_name, start_daf, start_amud, end_daf, end_amud)
        temp_file = os.path.join(temp_dir, filename)
        
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(combined_html)
        
        # Update progress - completed
        progress_data[task_id].update({
            'status': 'completed',
            'progress': 100,
            'message': 'הושלם! הקובץ מוכן להורדה',
            'filename': filename,
            'file_path': temp_file,
            'temp_dir': temp_dir  # Store temp_dir for cleanup later
        })
            
    except Exception as e:
        print(f"ERROR in background task: {e}")
        progress_data[task_id].update({
            'status': 'error',
            'message': f'שגיאה: {str(e)}'
        })

def create_combined_html(pages, tractate_name, start_daf, start_amud, end_daf, end_amud):
    """Create combined HTML from multiple pages"""
    title = f"{tractate_name} {start_daf} {start_amud} - {end_daf} {end_amud}"
    
    html = f"""<!DOCTYPE html>
<html dir="rtl" lang="he">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: 'Times New Roman', serif;
            direction: rtl;
            text-align: right;
            margin: 20px auto;
            max-width: 800px;
            line-height: 1.6;
        }}
        .page {{
            margin-bottom: 0;
            border-bottom: 1px dashed #ccc;
            padding-bottom: 10px;
        }}
        h1 {{
            color: #8B4513;
            border-bottom: 2px solid #8B4513;  
            padding-bottom: 10px;
            text-align: center;
        }}
        .page h1 {{
            text-align: right;
            font-size: 1.5em;
            margin-bottom: 5px;
            margin-top: 0px;
        }}
        .page p {{
            margin: 0.2em 0;
        }}
        span.big {{
            font-size: 1em;
            font-weight: normal;
            color: inherit;
        }}
        p > span.big:first-child {{
            font-size: 1.6em;
            font-weight: bold;
            color: #5a1a00;
            display: inline-block;
            min-width: 1.8em;
            vertical-align: baseline;
            line-height: 1;
        }}
        @media print {{
            .page {{
                border-bottom: none;
            }}
        }}
    </style>
</head>
<body>
    <h1>📖 {title}</h1>
"""
    
    for page in pages:
        soup = BeautifulSoup(page['content'], 'html.parser')
        
        # Extract title and content properly
        page_title = soup.find('h1')
        page_content = soup.find('body')
        
        html += f'<div class="page">\n'
        
        if page_title:
            html += f'<h1>{page_title.get_text().strip()}</h1>\n'
            
        if page_content:
            # Remove the h1 from content to avoid duplication
            content_copy = BeautifulSoup(str(page_content), 'html.parser')
            strip_kodat_widget(content_copy)
            title_in_content = content_copy.find('h1')
            if title_in_content:
                title_in_content.decompose()
            
            # Extract just the content div to avoid extra body/html structure
            content_div = content_copy.find('div', class_='content')
            if content_div:
                # More aggressive whitespace cleanup
                content_html = str(content_div)
                # Remove excessive newlines and whitespace
                content_html = re.sub(r'\n\s*\n+', '\n', content_html)
                content_html = re.sub(r'<p>\s*</p>', '', content_html)
                # Remove excessive spacing between paragraphs
                content_html = re.sub(r'</p>\s*<p>', '</p><p>', content_html)
                # Minimize margins and padding in paragraphs
                content_html = re.sub(r'<p>', '<p style="margin:0.2em 0;">', content_html)
                html += content_html
            else:
                # Fallback: use the body content but clean it up
                content_html = str(content_copy)
                content_html = re.sub(r'\n\s*\n+', '\n', content_html)
                content_html = re.sub(r'<p>\s*</p>', '', content_html)
                content_html = re.sub(r'</p>\s*<p>', '</p><p>', content_html)
                content_html = re.sub(r'<p>', '<p style="margin:0.2em 0;">', content_html)
                html += content_html
            
        html += '</div>\n\n'
    
    html += """</body>
</html>"""
    
    return html

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)