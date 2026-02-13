import streamlit as st
import csv
import re
import io

# --- CONFIGURATION ---
BADGE_MAP = {
    'gluten-free': {'label': 'GF', 'color': '#e67c23'},
    'gf':          {'label': 'GF', 'color': '#e67c23'},
    'vegan':       {'label': 'V',  'color': '#27ae60'},
    'organic':     {'label': 'Org', 'color': '#2980b9'},
    'local':       {'label': 'Loc', 'color': '#8e44ad'},
    'dairy-free':  {'label': 'DF', 'color': '#c0392b'},
    'keto':        {'label': 'Keto', 'color': '#16a085'},
}

SKIP_PHRASES = [
    "week of", "turn your phone", "update this list", 
    "items run out", "tax included", "easier to view"
]

def generate_badges(text):
    badges_html = ""
    lower_text = text.lower()
    for key, style in BADGE_MAP.items():
        if re.search(r'\b' + re.escape(key) + r'\b', lower_text):
            badges_html += f"<span class='cg-badge' style='background-color:{style['color']}'>{style['label']}</span>"
    return text + " " + badges_html

def parse_price_info(text):
    """Parses a price string using a waterfall approach."""
    info = {'std': 0.0, 'bulk': 0.0, 'thresh': 0}
    if not text: return info
    
    # Find all dollar amounts in the string
    prices = re.findall(r'\$(\d+\.?\d*)', text)
    
    # 1. Tiered Deal: "$2.00/each or $1.65/each for 6+"
    if '+' in text and len(prices) >= 2:
        info['std'] = float(prices[0])
        info['bulk'] = float(prices[1])
        thresh_match = re.search(r'(\d+)\+', text)
        if thresh_match:
            info['thresh'] = int(thresh_match.group(1))
        return info

    # 2. Bundle Deal: "$3 each / 6 for $15" OR "2/$5.99"
    bundle_match = re.search(r'(\d+)\s*(?:/|for)\s*\$(\d+\.?\d*)', text)
    if bundle_match:
        qty = int(bundle_match.group(1))
        total_bundle_price = float(bundle_match.group(2))
        
        if len(prices) >= 2 and float(prices[0]) != total_bundle_price:
            info['std'] = float(prices[0])
        else:
            info['std'] = total_bundle_price / qty
            
        info['bulk'] = total_bundle_price / qty
        info['thresh'] = qty
        return info

    # 3. Standard / Integer Fallback
    if len(prices) > 0:
        info['std'] = float(prices[0])
        return info
        
    # 4. Raw Number Fallback (If they forgot the $ sign, e.g., "4.99")
    raw_match = re.search(r'(\d+\.\d{2})', text)
    if raw_match:
        info['std'] = float(raw_match.group(1))

    return info

def get_html_template(sections, body_content):
    js_sections = "const sections = [\n"
    for title, sid in sections:
        js_sections += f"{{Title: '{title}', Id: '{sid}'}},\n"
    js_sections += "];"

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>Core Goods Order</title>
<style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: #fafafa; color: #333; margin: 0; padding-bottom: 100px; }}
    .cg-app {{ max-width: 800px; margin: 0 auto; background: white; min-height: 100vh; position: relative; }}
    .cg-controls {{ position: sticky; top: 0; background: white; padding: 15px; border-bottom: 1px solid #eee; z-index: 100; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }}
    .cg-search {{ width: 100%; padding: 12px 15px; border: 2px solid #ddd; border-radius: 8px; font-size: 16px; outline: none; box-sizing: border-box; -webkit-appearance: none; }}
    .cg-search:focus {{ border-color: #2c5e2e; }}
    .cg-nav {{ overflow-x: auto; white-space: nowrap; padding: 10px 0 0 0; -webkit-overflow-scrolling: touch; scrollbar-width: none; }}
    .cg-nav::-webkit-scrollbar {{ display: none; }}
    .cg-nav a {{ display: inline-block; padding: 6px 12px; margin-right: 8px; background: #f4f4f4; border-radius: 20px; text-decoration: none; color: #444; font-size: 14px; font-weight: 600; }}
    .cg-nav a.active {{ background: #2c5e2e; color: white; }}
    .cg-content {{ padding: 0 15px 40px 15px; }}
    .cg-section-title {{ color: #2c5e2e; margin-top: 35px; border-bottom: 2px solid #2c5e2e; padding-bottom: 5px; font-size: 1.3em; scroll-margin-top: 150px; }}
    .cg-item-row {{ display: flex; justify-content: space-between; align-items: start; padding: 15px 0; border-bottom: 1px solid #eee; min-height: 50px; }}
    .cg-item-info {{ flex: 1; padding-right: 15px; }}
    .cg-name {{ font-weight: 700; display: block; font-size: 1.05em; margin-bottom: 4px; color: #222; }}
    .cg-meta {{ font-size: 0.9em; color: #666; line-height: 1.4; display: block; margin-bottom: 4px; }}
    .cg-price {{ font-weight: 700; color: #2c5e2e; font-size: 1.1em; }}
    .cg-price.unknown {{ color: #999; font-weight: normal; font-size: 0.9em; }}
    .cg-subheader {{ background: #e8f5e9; padding: 8px 12px; font-weight: 700; color: #1b4d20; border-radius: 6px; margin-top: 20px; font-size: 0.95em; }}
    .cg-badge {{ display: inline-block; font-size: 0.7em; color: white; padding: 2px 6px; border-radius: 4px; margin-left: 6px; vertical-align: middle; font-weight: 700; text-transform: uppercase; }}
    
    .cg-qty-wrapper {{ display: flex; align-items: center; background: #f4f4f4; border-radius: 25px; height: 36px; padding: 2px; }}
    .cg-qty-btn {{ width: 32px; height: 32px; border-radius: 50%; border: none; background: white; cursor: pointer; font-weight: bold; font-size: 18px; color: #2c5e2e; display: flex; align-items: center; justify-content: center; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
    .cg-qty-val {{ min-width: 24px; text-align: center; font-weight: bold; font-size: 14px; color: #333; }}
    .cg-add-btn {{ background: #2c5e2e; color: white; border: none; width: 36px; height: 36px; border-radius: 50%; font-size: 20px; cursor: pointer; display: flex; align-items: center; justify-content: center; }}
    .hidden {{ display: none !important; }}

    .cg-checkout-bar {{ position: fixed; bottom: 30px; left: 50%; transform: translateX(-50%) translateY(150px); background: #222; color: white; padding: 12px 30px; border-radius: 50px; font-weight: bold; cursor: pointer; box-shadow: 0 5px 20px rgba(0,0,0,0.3); z-index: 900; display: flex; align-items: center; gap: 10px; transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275); min-width: 200px; justify-content: center; }}
    .cg-checkout-bar.visible {{ transform: translateX(-50%) translateY(0); }}

    .cg-top-btn {{ position: fixed; bottom: 100px; right: 20px; background: rgba(255,255,255,0.9); color: #2c5e2e; border: 1px solid #ddd; width: 45px; height: 45px; border-radius: 50%; font-size: 20px; display: flex; align-items: center; justify-content: center; cursor: pointer; opacity: 0; transition: opacity 0.3s; pointer-events: none; z-index: 800; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
    .cg-top-btn.visible {{ opacity: 1; pointer-events: auto; }}

    .cg-modal-overlay {{ position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); z-index: 1000; display: none; align-items: flex-end; justify-content: center; backdrop-filter: blur(2px); }}
    .cg-modal-overlay.open {{ display: flex; }}
    .cg-modal {{ background: white; width: 100%; max-width: 600px; border-radius: 20px 20px 0 0; padding: 25px; box-sizing: border-box; max-height: 85vh; display: flex; flex-direction: column; animation: slideUp 0.3s ease-out; }}
    @keyframes slideUp {{ from {{ transform: translateY(100%); }} to {{ transform: translateY(0); }} }}
    .cg-modal-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 1px solid #eee; padding-bottom: 15px; }}
    .cg-modal-title {{ font-size: 1.5em; font-weight: bold; color: #2c5e2e; margin: 0; }}
    .cg-close-btn {{ background: none; border: none; font-size: 24px; color: #999; cursor: pointer; padding: 0 10px; }}
    .cg-empty-btn {{ background: none; border: 1px solid #e74c3c; color: #e74c3c; border-radius: 4px; padding: 5px 10px; font-size: 0.8em; font-weight: bold; cursor: pointer; margin-right: auto; margin-left: 15px; }}
    .cg-cart-list {{ overflow-y: auto; flex: 1; margin-bottom: 20px; }}
    .cg-cart-item {{ display: flex; justify-content: space-between; align-items: center; padding: 15px 0; border-bottom: 1px solid #f5f5f5; }}
    .cg-cart-name {{ font-weight: 600; flex: 1; padding-right: 10px; }}
    .cg-cart-controls {{ display: flex; align-items: center; gap: 10px; background: #f9f9f9; padding: 5px; border-radius: 20px; }}
    .cg-cart-footer {{ border-top: 1px solid #eee; padding-top: 20px; }}
    .cg-total-row {{ display: flex; justify-content: space-between; font-size: 1.2em; font-weight: bold; margin-bottom: 20px; }}
    .cg-send-btn {{ background: #2c5e2e; color: white; width: 100%; padding: 15px; border: none; border-radius: 12px; font-size: 1.1em; font-weight: bold; cursor: pointer; text-align: center; display: block; text-decoration: none; }}
</style>
</head>
<body>
<div class="cg-app">
    <div class="cg-controls">
        <input type="text" id="cgSearch" class="cg-search" placeholder="Search menu...">
        <div class="cg-nav" id="cgNav"></div>
    </div>
    <div class="cg-content" id="cgList">
        {body_content}
    </div>
</div>
<button id="cgTopBtn" class="cg-top-btn" onclick="window.scrollTo({{top:0, behavior:'smooth'}})">↑</button>
<div id="checkoutBar" class="cg-checkout-bar" onclick="openCart()">
    <span>🛒 Review Order</span>
    <span id="cartCount" style="background: white; color: black; padding: 2px 8px; border-radius: 10px; font-size: 0.9em; margin-left: 8px;">0</span>
</div>
<div id="cartModal" class="cg-modal-overlay">
    <div class="cg-modal">
        <div class="cg-modal-header">
            <div class="cg-modal-title">Your Order</div>
            <button class="cg-empty-btn" onclick="emptyCart()">Empty Cart</button>
            <button class="cg-close-btn" onclick="closeCart()">&times;</button>
        </div>
        <div class="cg-cart-list" id="cartList"></div>
        <div class="cg-cart-footer">
            <div class="cg-total-row">
                <span>Total Estimate:</span>
                <span id="cartTotal">$0.00</span>
            </div>
            <button class="cg-send-btn" onclick="sendEmail()">Send Order via Email</button>
        </div>
    </div>
</div>
<script>
    {js_sections}
    let cart = {{}}; 
    
    function updateQty(name, price, bulkPrice, bulkThresh, rawPrice, change) {{
        if (!cart[name]) cart[name] = {{ qty: 0, price: price, bulkPrice: bulkPrice, bulkThresh: bulkThresh, raw: rawPrice }};
        cart[name].qty += change;
        if (cart[name].qty <= 0) {{ delete cart[name]; updateItemControls(name, 0); }}
        else {{ updateItemControls(name, cart[name].qty); }}
        updateUI();
        if(document.getElementById('cartModal').classList.contains('open')) renderCartItems();
    }}

    function updateItemControls(name, qty) {{
        const safeId = 'ctrl-' + name.replace(/[^a-zA-Z0-9]/g, "");
        const wrapper = document.getElementById(safeId);
        if(!wrapper) return;
        if (qty > 0) {{
            wrapper.innerHTML = `<button class="cg-qty-btn" onclick="triggerUpdate('${{name}}', -1)">-</button><div class="cg-qty-val">${{qty}}</div><button class="cg-qty-btn" onclick="triggerUpdate('${{name}}', 1)">+</button>`;
        }} else {{
            const d = wrapper.dataset;
            wrapper.innerHTML = `<button class="cg-add-btn" onclick="updateQty('${{name}}', ${{d.p}}, ${{d.bp}}, ${{d.bt}}, '${{d.r}}', 1)">+</button>`;
        }}
    }}

    window.triggerUpdate = function(name, change) {{
        const safeId = 'ctrl-' + name.replace(/[^a-zA-Z0-9]/g, "");
        const wrapper = document.getElementById(safeId);
        updateQty(name, parseFloat(wrapper.dataset.p), parseFloat(wrapper.dataset.bp), parseInt(wrapper.dataset.bt), wrapper.dataset.r, change);
    }}

    function emptyCart() {{
        if(Object.keys(cart).length === 0) return;
        if(confirm("Are you sure you want to empty your cart?")) {{
            for (const name in cart) updateItemControls(name, 0);
            cart = {{}}; updateUI(); renderCartItems(); closeCart();
        }}
    }}

    function calculateTotal() {{
        let totalCents = 0; let count = 0;
        for (const [name, item] of Object.entries(cart)) {{
            count += item.qty;
            let p = (item.bulkThresh > 0 && item.qty >= item.bulkThresh) ? item.bulkPrice : item.price;
            totalCents += Math.round(p * item.qty * 100);
        }}
        return {{ count: count, total: (totalCents / 100).toFixed(2) }};
    }}

    function updateUI() {{
        const res = calculateTotal();
        document.getElementById('cartCount').innerText = res.count;
        document.getElementById('cartTotal').innerText = '$' + res.total;
        const bar = document.getElementById('checkoutBar');
        if (res.count > 0) bar.classList.add('visible'); else bar.classList.remove('visible');
    }}

    function renderCartItems() {{
        const container = document.getElementById('cartList');
        container.innerHTML = "";
        if (Object.keys(cart).length === 0) {{ container.innerHTML = "<p style='text-align:center; color:#999;'>Your cart is empty.</p>"; return; }}
        for (const [name, item] of Object.entries(cart)) {{
            let p = item.price; let note = "";
            if (item.bulkThresh > 0 && item.qty >= item.bulkThresh) {{ p = item.bulkPrice; note = `<span style="color:#27ae60; font-size:0.8em; margin-left:5px;">(Bulk!)</span>`; }}
            else if (item.bulkThresh > 0) {{ note = `<span style="color:#e67c23; font-size:0.8em; margin-left:5px;">(Buy ${{item.bulkThresh}} for $${{item.bulkPrice.toFixed(2)}} ea)</span>`; }}
            container.innerHTML += `<div class="cg-cart-item"><div class="cg-cart-name">${{name}} ${{note}}<br><span style="font-weight:normal; font-size:0.85em; color:#666;">@ $${{p.toFixed(2)}}</span></div><div class="cg-cart-controls"><button class="cg-qty-btn" onclick="triggerUpdate('${{name}}', -1)">-</button><span class="cg-qty">${{item.qty}}</span><button class="cg-qty-btn" onclick="triggerUpdate('${{name}}', 1)">+</button></div></div>`;
        }}
    }}

    function openCart() {{ renderCartItems(); document.getElementById('cartModal').classList.add('open'); document.body.style.overflow = 'hidden'; }}
    function closeCart() {{ document.getElementById('cartModal').classList.remove('open'); document.body.style.overflow = ''; }}

    function sendEmail() {{
        let body = "Hi Core Goods,\\n\\nI'd like to place an order for pickup:\\n\\n";
        for (const [name, item] of Object.entries(cart)) {{
            let p = (item.bulkThresh > 0 && item.qty >= item.bulkThresh) ? item.bulkPrice : item.price;
            let lbl = (p < item.price) ? " (BULK)" : "";
            body += `- [${{item.qty}}x] ${{name}} @ $${{p.toFixed(2)}}${{lbl}}\\n`;
        }}
        const res = calculateTotal();
        body += `\\nEstimated Total: $${{res.total}}\\n\\nThanks!`;
        window.location.href = `mailto:coregoodsoc@gmail.com?subject=Order%20for%20Pickup&body=${{encodeURIComponent(body)}}`;
    }}

    const nav = document.getElementById('cgNav');
    sections.forEach(s => {{
        const a = document.createElement('a'); a.innerText = s.Title; a.href = "#" + s.Id;
        a.onclick = (e) => {{ e.preventDefault(); document.querySelectorAll('.cg-nav a').forEach(l => l.classList.remove('active')); e.target.classList.add('active'); document.getElementById(s.Id).scrollIntoView({{ behavior: 'smooth', block: 'start' }}); }};
        nav.appendChild(a);
    }});
    document.getElementById('cgSearch').addEventListener('keyup', (e) => {{
        const term = e.target.value.toLowerCase();
        document.querySelectorAll('.cg-item-row').forEach(row => {{
            const txt = row.getAttribute('data-search');
            row.style.display = txt.includes(term) ? 'flex' : 'none';
        }});
    }});
    document.getElementById('cartModal').addEventListener('click', (e) => {{ if (e.target === document.getElementById('cartModal')) closeCart(); }});
    window.addEventListener('scroll', () => {{
        const btn = document.getElementById('cgTopBtn');
        if (window.scrollY > 400) btn.classList.add('visible'); else btn.classList.remove('visible');
    }});
</script>
</body>
</html>
    """

# --- REUSABLE LOGIC (Separated from UI) ---
def convert_data_to_html(file_obj):
    reader = csv.reader(file_obj)
    sections = []
    body_content = ""
    
    for row in reader:
        row = [c.strip() for c in row]
        if not any(row): continue
        
        # 0. JUNK FILTER
        line_text = " ".join(row).lower()
        if any(phrase in line_text for phrase in SKIP_PHRASES): continue

        # 1. Section Header
        if row[0].isupper() and len(row[0]) > 3 and not row[1]:
            sid = row[0].lower().replace(' ', '-')
            while any(s[1] == sid for s in sections): sid += "-x"
            sections.append((row[0], sid))
            body_content += f"<h2 id='{sid}' class='cg-section-title'>{row[0]}</h2>"
            continue
        
        # 2. Skip Table Headers
        if row[0].lower().startswith("item"): continue

        # 3. Handle Items
        if row[0]:
            base_name = row[0].replace('"', '&quot;')
            raw_price_str = row[1] if len(row) > 1 else ""
            notes = " ".join(row[2:]) if len(row) > 2 else ""
            
            # --- THE MAGIC FIX ---
            # Look for explicit sizes (sm, lg, pt, qt, half, whole) next to a price
            size_matches = re.findall(r'\$?(\d+(?:\.\d{2})?)\s*(sm|lg|small|large|pt|qt|pint|quart|half|whole)\b', raw_price_str, re.IGNORECASE)
            
            items_to_render = []
            
            # If we find MULTIPLE sizes in one row, we split them into distinct products
            if len(size_matches) > 1:
                for price_val, size_lbl in size_matches:
                    items_to_render.append({
                        'name': f"{base_name} ({size_lbl})",
                        'price_str': f"${price_val}",
                        'notes': notes
                    })
            else:
                # Normal behavior for standard items or bundle deals
                items_to_render.append({
                    'name': base_name,
                    'price_str': raw_price_str,
                    'notes': notes
                })

            # Render HTML for each item (or split items)
            for item in items_to_render:
                name = item['name']
                price_str = item['price_str']
                item_notes = item['notes']
                
                p_info = parse_price_info(price_str)
                display_price = price_str if price_str else "See details"
                
                button_html = ""
                if p_info['std'] > 0:
                    safe_id = re.sub(r'[^a-zA-Z0-9]', '', name)
                    ctrl_id = 'ctrl-' + safe_id
                    
                    button_html = f"""
                    <div class="cg-qty-wrapper" 
                         id="{ctrl_id}"
                         data-p="{p_info['std']}"
                         data-bp="{p_info['bulk']}"
                         data-bt="{p_info['thresh']}"
                         data-r="{display_price}">
                        <button class="cg-add-btn" 
                                onclick="updateQty('{name}', {p_info['std']}, {p_info['bulk']}, {p_info['thresh']}, '{display_price}', 1)">
                            +
                        </button>
                    </div>
                    """
                
                price_class = "cg-price" if p_info['std'] > 0 else "cg-price unknown"

                body_content += f"""
                <div class="cg-item-row" data-search="{name.lower()} {item_notes.lower()}">
                    <div class="cg-item-info">
                        <span class="cg-name">{name}</span>
                        <span class="cg-meta">{generate_badges(item_notes)}</span>
                        <span class="{price_class}">{display_price}</span>
                    </div>
                    {button_html}
                </div>
                """

    return get_html_template(sections, body_content)

# --- MAIN UI (Protected by __main__) ---
if __name__ == "__main__":
    st.set_page_config(page_title="Core Goods Generator", page_icon="🥬", layout="centered")
    st.title("🥬 Core Goods Menu Generator")
    st.markdown("Upload your weekly `CSV` file to generate the updated mobile-friendly website.")

    uploaded_file = st.file_uploader("Upload CSV", type="csv")

    if uploaded_file is not None:
        stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8", errors='replace'))
        full_html = convert_data_to_html(stringio)

        st.success("✅ Conversion Complete!")
        
        st.download_button(
            label="Download Website HTML",
            data=full_html,
            file_name="core_goods_menu.html",
            mime="text/html"
        )

        st.subheader("Preview")
        st.components.v1.html(full_html, height=600, scrolling=True)