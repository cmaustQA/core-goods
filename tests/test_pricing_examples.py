from convert_menu import parse_price_info

def test_weird_formats():
    examples = [
        # (Input String, Expected Standard, Expected Threshold)
        ("$3.29", 3.29, 0),
        ("2/$5.99", 2.995, 2),
        ("$2.00/each or $1.65/each for 6+", 2.00, 6),
        ("$5", 5.0, 0),
        ("approx $4.50 / lb", 4.50, 0), # Messy text
        ("2 for $5", 2.50, 2)           # Word variation
    ]

    print("\n--- Testing Price Parser ---")
    for text, exp_std, exp_thresh in examples:
        result = parse_price_info(text)
        status = "✅" if result['std'] == exp_std else "❌"
        print(f"{status} Input: '{text}'")
        print(f"   -> Parsed: ${result['std']} (Thresh: {result['thresh']})")
        
        # Optional: Fail the test if math is wrong
        assert result['std'] == exp_std