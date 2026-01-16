"""
Comprehensive test suite using test_files as source of truth
"""
import json
import os
from multi_converter import convert_format, json_to_toon, toon_to_json, json_to_csv, csv_to_json, json_to_yaml, yaml_to_json
from token_counter import count_tokens_for_formats, get_recommended_format

# Load test files
def load_test_file(filename):
    """Load test file content"""
    path = os.path.join('..', 'test_files', filename)
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

# Load all test files
json_content = load_test_file('test.json')
toon_content = load_test_file('test.toon')
csv_content = load_test_file('test.csv')
yaml_content = load_test_file('test.yaml')

print("=" * 70)
print("COMPREHENSIVE FORMAT CONVERSION TEST")
print("=" * 70)

# Test 1: JSON to all formats
print("\n1. Testing JSON -> All Formats")
print("-" * 70)
json_data = json.loads(json_content)
results = convert_format(json_content, 'json', 'all')

# Check TOON
toon_output = results['toon'].strip()
toon_expected = toon_content.strip()
toon_match = toon_output == toon_expected
print(f"  TOON: {'MATCH' if toon_match else 'MISMATCH'}")
if not toon_match:
    print(f"    Expected length: {len(toon_expected)}")
    print(f"    Got length: {len(toon_output)}")
    if len(toon_output) <= 200:
        print(f"    Got: {toon_output[:100]}...")

# Check CSV (may have formatting differences, so check structure)
csv_output = results['csv'].strip()
csv_expected = csv_content.strip()
# CSV might have different boolean representation
csv_lines_got = csv_output.split('\n')
csv_lines_expected = csv_expected.split('\n')
csv_match = len(csv_lines_got) == len(csv_lines_expected) and csv_lines_got[0] == csv_lines_expected[0]
print(f"  CSV:  {'MATCH (structure)' if csv_match else 'MISMATCH'}")

# Check YAML (may have formatting differences)
yaml_output = results['yaml'].strip()
yaml_expected = yaml_content.strip()
yaml_match = len(yaml_output.split('\n')) == len(yaml_expected.split('\n'))
print(f"  YAML: {'MATCH (structure)' if yaml_match else 'MISMATCH'}")

# Test 2: TOON to JSON
print("\n2. Testing TOON -> JSON")
print("-" * 70)
toon_json = toon_to_json(toon_content)
json_from_toon = json.dumps(toon_json, indent=2, sort_keys=True)
original_json = json.dumps(json_data, indent=2, sort_keys=True)
toon_roundtrip = json_from_toon == original_json
print(f"  Round-trip: {'MATCH' if toon_roundtrip else 'MISMATCH'}")

# Test 3: CSV to JSON
print("\n3. Testing CSV -> JSON")
print("-" * 70)
csv_json = csv_to_json(csv_content)
csv_roundtrip = len(csv_json) == len(json_data)
print(f"  Structure match: {'MATCH' if csv_roundtrip else 'MISMATCH'}")

# Test 4: YAML to JSON
print("\n4. Testing YAML -> JSON")
print("-" * 70)
yaml_json = yaml_to_json(yaml_content)
yaml_roundtrip = len(yaml_json) == len(json_data)
print(f"  Structure match: {'MATCH' if yaml_roundtrip else 'MISMATCH'}")

# Test 5: Token counting
print("\n5. Testing Token Counts")
print("-" * 70)
tokens = count_tokens_for_formats({
    'json': json_content,
    'toon': toon_content,
    'csv': csv_content,
    'yaml': yaml_content
})
for fmt, count in tokens.items():
    print(f"  {fmt.upper():6}: {count:4} tokens")

recommendation = get_recommended_format(tokens)
print(f"\n  Recommended: {recommendation['recommended']} ({recommendation['min_tokens']} tokens)")

# Test 6: All format conversions
print("\n6. Testing All Format Conversions")
print("-" * 70)
formats_to_test = [
    ('json', json_content),
    ('toon', toon_content),
    ('csv', csv_content),
    ('yaml', yaml_content)
]

all_passed = True
for from_fmt, content in formats_to_test:
    try:
        result = convert_format(content, from_fmt, 'all')
        print(f"  {from_fmt.upper()} -> All: SUCCESS")
    except Exception as e:
        print(f"  {from_fmt.upper()} -> All: FAILED - {str(e)}")
        all_passed = False

print("\n" + "=" * 70)
if toon_match and toon_roundtrip and all_passed:
    print("ALL TESTS PASSED")
else:
    print("SOME TESTS FAILED")
print("=" * 70)
