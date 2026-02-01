import pytest
from playwright.sync_api import Page, expect
import os
import re

# Point this to where you saved the HTML file
HTML_PATH = os.path.abspath("tests/sample_menu.html")

@pytest.fixture(scope="function")
def menu_page(page: Page):
    """Fixture to load the HTML file before each test"""
    page.goto(f"file://{HTML_PATH}")
    return page

def test_add_item_to_cart(menu_page: Page):
    """Test clicking '+' changes button to counter and updates cart"""
    # Find the first 'Add' button
    add_btn = menu_page.locator(".cg-add-btn").first
    add_btn.click()
    
    # Check if it changed to the Quantity Control
    qty_val = menu_page.locator(".cg-qty-val").first
    expect(qty_val).to_be_visible()
    expect(qty_val).to_have_text("1")
    
    # Check Floating Bar appeared
    checkout_bar = menu_page.locator("#checkoutBar")
    expect(checkout_bar).to_be_visible()
    expect(menu_page.locator("#cartCount")).to_have_text("1")

def test_search_functionality(menu_page: Page):
    """Test that typing in search hides non-matching items"""
    search_input = menu_page.locator("#cgSearch")
    
    # Use 'type' with delay to ensure JS events fire correctly
    search_input.type("zzzzzz", delay=100)
    
    # Wait for DOM update
    menu_page.wait_for_timeout(500)
    
    rows = menu_page.locator(".cg-item-row")
    
    # Count visible rows
    visible_count = 0
    for i in range(rows.count()):
        if rows.nth(i).is_visible():
            visible_count += 1
            
    # Everything should be hidden
    assert visible_count == 0 

def test_bulk_pricing_math(menu_page: Page):
    """
    Test the JS math engine.
    FIX: We now read the 'data-p' attribute to get the price the app 
    is actually using, rather than parsing the messy display text.
    """
    # 1. Find all rows that actually HAVE an add button
    shoppable_rows = menu_page.locator(".cg-item-row", has=menu_page.locator(".cg-add-btn"))
    
    assert shoppable_rows.count() >= 2
    
    # --- ITEM 1 ---
    row1 = shoppable_rows.nth(0)
    # Read the 'data-p' attribute (The canonical price)
    price1 = float(row1.locator(".cg-qty-wrapper").get_attribute("data-p"))
    row1.locator(".cg-add-btn").click()
    
    # --- ITEM 2 ---
    row2 = shoppable_rows.nth(1)
    # Read the 'data-p' attribute
    price2 = float(row2.locator(".cg-qty-wrapper").get_attribute("data-p"))
    row2.locator(".cg-add-btn").click()

    # 4. Calculate Expected Total
    expected_total = price1 + price2
    
    # 5. Compare with Cart Total
    total_text = menu_page.locator("#cartTotal").inner_text()
    actual_total = float(total_text.replace("$", ""))
    
    # Use approx for float comparison
    assert actual_total == pytest.approx(expected_total, 0.01)

def test_cart_modal_flow(menu_page: Page):
    """Test opening cart, removing item, checking total"""
    # Add an item
    menu_page.locator(".cg-add-btn").first.click()
    
    # Open Cart
    menu_page.locator("#checkoutBar").click()
    
    # Check Modal is open
    modal = menu_page.locator("#cartModal")
    expect(modal).to_have_class(re.compile(r"open"))
    
    # Increase qty inside modal
    menu_page.locator(".cg-cart-controls .cg-qty-btn").nth(1).click() # Click +
    
    # Check qty updated
    expect(menu_page.locator(".cg-cart-controls .cg-qty")).to_have_text("2")
    
    # Close Cart
    menu_page.locator(".cg-close-btn").click()
    expect(modal).not_to_have_class(re.compile(r"open"))