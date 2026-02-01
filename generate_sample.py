import os
from convert_menu import convert_data_to_html

# Path to your test CSV and output HTML
INPUT_CSV = "Core Goods Product List - Sheet1.csv"
OUTPUT_HTML = "tests/sample_menu.html"

def main():
    if not os.path.exists(INPUT_CSV):
        print(f"❌ Error: Cannot find {INPUT_CSV}")
        return

    print(f"Reading from {INPUT_CSV}...")
    
    with open(INPUT_CSV, "r", encoding="utf-8") as f:
        # We pass the file object directly to the function we refactored
        html_content = convert_data_to_html(f)
    
    # Ensure tests dir exists
    os.makedirs(os.path.dirname(OUTPUT_HTML), exist_ok=True)
    
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"✅ Success! Generated {OUTPUT_HTML}")

if __name__ == "__main__":
    main()