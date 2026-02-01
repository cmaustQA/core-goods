import pytest
from convert_menu import parse_price_info, generate_badges, SKIP_PHRASES

# 1. TEST PRICE EXTRACTION
def test_standard_price():
    """Test standard $X.XX format"""
    res = parse_price_info("$5.99")
    assert res['std'] == 5.99
    assert res['bulk'] == 0.0

def test_integer_price():
    """Test integer prices like $5"""
    res = parse_price_info("$5")
    assert res['std'] == 5.0
    
def test_bulk_pricing():
    """Test the complex bulk string format"""
    input_str = "$2.00/each or $1.65/each for 6+"
    res = parse_price_info(input_str)
    assert res['std'] == 2.00
    assert res['bulk'] == 1.65
    assert res['thresh'] == 6

def test_empty_price():
    """Test empty or text-only price columns"""
    assert parse_price_info("")['std'] == 0.0
    assert parse_price_info("See details")['std'] == 0.0

# 2. TEST BADGES
def test_badge_generation():
    html = generate_badges("Vegan Gluten-Free Cookies")
    # Check for color codes from your BADGE_MAP
    assert "background-color:#27ae60" in html # Green (Vegan)
    assert "background-color:#e67c23" in html # Orange (GF)

def test_no_badges():
    html = generate_badges("Regular Sourdough Bread")
    assert "span class='cg-badge'" not in html

# 3. TEST JUNK FILTER
def test_skip_phrases():
    """Ensure junk rows are caught by the filter list"""
    junk_row = "Core Goods Item List - Week of 1/28/26"
    assert any(phrase in junk_row.lower() for phrase in SKIP_PHRASES)

    valid_row = "Sourdough Bread"
    assert not any(phrase in valid_row.lower() for phrase in SKIP_PHRASES)