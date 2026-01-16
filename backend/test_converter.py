"""
Extensive test cases for JSON to TOON conversion
"""
import pytest
from converter import json_to_toon


class TestBasicTypes:
    """Test basic data types"""
    
    def test_string_value(self):
        """Test simple string value"""
        json_data = {"name": "John"}
        result = json_to_toon(json_data)
        assert result == "name: John"
    
    def test_integer_value(self):
        """Test integer value"""
        json_data = {"age": 30}
        result = json_to_toon(json_data)
        assert result == "age: 30"
    
    def test_float_value(self):
        """Test float value"""
        json_data = {"price": 99.99}
        result = json_to_toon(json_data)
        assert result == "price: 99.99"
    
    def test_boolean_true(self):
        """Test boolean true value"""
        json_data = {"active": True}
        result = json_to_toon(json_data)
        assert result == "active: True"
    
    def test_boolean_false(self):
        """Test boolean false value"""
        json_data = {"active": False}
        result = json_to_toon(json_data)
        assert result == "active: False"
    
    def test_null_value(self):
        """Test null/None value"""
        json_data = {"value": None}
        result = json_to_toon(json_data)
        assert result == "value: None"
    
    def test_zero_value(self):
        """Test zero value"""
        json_data = {"count": 0}
        result = json_to_toon(json_data)
        assert result == "count: 0"
    
    def test_empty_string(self):
        """Test empty string"""
        json_data = {"description": ""}
        result = json_to_toon(json_data)
        assert result == "description: "


class TestSimpleObjects:
    """Test simple JSON objects"""
    
    def test_single_key_value(self):
        """Test object with single key-value pair"""
        json_data = {"name": "Alice"}
        result = json_to_toon(json_data)
        assert result == "name: Alice"
    
    def test_multiple_key_values(self):
        """Test object with multiple key-value pairs"""
        json_data = {"name": "Bob", "age": 25, "city": "London"}
        result = json_to_toon(json_data)
        expected = "name: Bob\nage: 25\ncity: London"
        assert result == expected
    
    def test_mixed_types(self):
        """Test object with mixed data types"""
        json_data = {
            "name": "Charlie",
            "age": 35,
            "salary": 50000.50,
            "active": True,
            "score": None
        }
        result = json_to_toon(json_data)
        assert "name: Charlie" in result
        assert "age: 35" in result
        assert "salary: 50000.5" in result or "salary: 50000.50" in result
        assert "active: True" in result
        assert "score: None" in result


class TestNestedObjects:
    """Test nested JSON objects"""
    
    def test_one_level_nesting(self):
        """Test one level of nesting"""
        json_data = {
            "person": {
                "name": "David",
                "age": 40
            }
        }
        result = json_to_toon(json_data)
        expected = "person:\n  name: David\n  age: 40"
        assert result == expected
    
    def test_two_level_nesting(self):
        """Test two levels of nesting"""
        json_data = {
            "user": {
                "profile": {
                    "name": "Eve",
                    "email": "eve@example.com"
                }
            }
        }
        result = json_to_toon(json_data)
        expected = "user:\n  profile:\n    name: Eve\n    email: eve@example.com"
        assert result == expected
    
    def test_deep_nesting(self):
        """Test deep nesting (3+ levels)"""
        json_data = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": "deep value"
                    }
                }
            }
        }
        result = json_to_toon(json_data)
        assert "level1:" in result
        assert "  level2:" in result
        assert "    level3:" in result
        assert "      level4: deep value" in result
    
    def test_multiple_nested_objects(self):
        """Test multiple nested objects at same level"""
        json_data = {
            "address": {
                "street": "123 Main St",
                "city": "New York"
            },
            "contact": {
                "phone": "555-1234",
                "email": "test@example.com"
            }
        }
        result = json_to_toon(json_data)
        assert "address:" in result
        assert "  street: 123 Main St" in result
        assert "  city: New York" in result
        assert "contact:" in result
        assert "  phone: 555-1234" in result
        assert "  email: test@example.com" in result


class TestArrays:
    """Test JSON arrays"""
    
    def test_empty_array(self):
        """Test empty array"""
        json_data = {"items": []}
        result = json_to_toon(json_data)
        # Empty array produces empty string, so we get just the key with newline
        assert result == "items:\n" or result == "items:"
    
    def test_simple_array_strings(self):
        """Test array of strings"""
        json_data = {"tags": ["red", "blue", "green"]}
        result = json_to_toon(json_data)
        # When array is inside an object, it includes the key and proper indentation
        expected = "tags:\n  [0]: red\n  [1]: blue\n  [2]: green"
        assert result == expected
    
    def test_simple_array_numbers(self):
        """Test array of numbers"""
        json_data = {"scores": [100, 95, 87, 92]}
        result = json_to_toon(json_data)
        assert "[0]: 100" in result
        assert "[1]: 95" in result
        assert "[2]: 87" in result
        assert "[3]: 92" in result
    
    def test_mixed_type_array(self):
        """Test array with mixed types"""
        json_data = {"mixed": ["text", 123, True, None, 45.67]}
        result = json_to_toon(json_data)
        assert "[0]: text" in result
        assert "[1]: 123" in result
        assert "[2]: True" in result
        assert "[3]: None" in result
        assert "[4]: 45.67" in result or "[4]: 45.67" in result
    
    def test_array_of_objects(self):
        """Test array containing objects"""
        json_data = {
            "users": [
                {"name": "Alice", "age": 25},
                {"name": "Bob", "age": 30}
            ]
        }
        result = json_to_toon(json_data)
        assert "users:" in result
        assert "  [0]:" in result
        assert "    name: Alice" in result
        assert "    age: 25" in result
        assert "  [1]:" in result
        assert "    name: Bob" in result
        assert "    age: 30" in result
    
    def test_array_of_arrays(self):
        """Test nested arrays"""
        json_data = {"matrix": [[1, 2], [3, 4]]}
        result = json_to_toon(json_data)
        assert "matrix:" in result
        assert "  [0]:" in result
        assert "    [0]: 1" in result
        assert "    [1]: 2" in result
        assert "  [1]:" in result
        assert "    [0]: 3" in result
        assert "    [1]: 4" in result


class TestComplexStructures:
    """Test complex nested structures"""
    
    def test_object_with_array_and_nested_object(self):
        """Test object containing both arrays and nested objects"""
        json_data = {
            "person": {
                "name": "Frank",
                "hobbies": ["reading", "coding", "gaming"],
                "address": {
                    "street": "456 Oak Ave",
                    "zip": "12345"
                }
            }
        }
        result = json_to_toon(json_data)
        assert "person:" in result
        assert "  name: Frank" in result
        assert "  hobbies:" in result
        assert "    [0]: reading" in result
        assert "  address:" in result
        assert "    street: 456 Oak Ave" in result
    
    def test_array_with_nested_objects_and_arrays(self):
        """Test array containing objects with nested arrays"""
        json_data = {
            "employees": [
                {
                    "name": "Grace",
                    "skills": ["Python", "JavaScript"]
                },
                {
                    "name": "Henry",
                    "skills": ["Java", "C++"]
                }
            ]
        }
        result = json_to_toon(json_data)
        assert "employees:" in result
        assert "  [0]:" in result
        assert "    name: Grace" in result
        assert "    skills:" in result
        assert "      [0]: Python" in result
    
    def test_real_world_example(self):
        """Test a realistic JSON structure"""
        json_data = {
            "company": "Tech Corp",
            "employees": [
                {
                    "id": 1,
                    "name": "Alice",
                    "department": "Engineering",
                    "projects": ["Project A", "Project B"],
                    "active": True
                },
                {
                    "id": 2,
                    "name": "Bob",
                    "department": "Marketing",
                    "projects": ["Project C"],
                    "active": False
                }
            ],
            "locations": {
                "headquarters": {
                    "city": "San Francisco",
                    "country": "USA"
                },
                "offices": ["New York", "London", "Tokyo"]
            }
        }
        result = json_to_toon(json_data)
        # Verify key components
        assert "company: Tech Corp" in result
        assert "employees:" in result
        assert "  [0]:" in result
        assert "    name: Alice" in result
        assert "locations:" in result
        assert "  headquarters:" in result
        assert "    city: San Francisco" in result


class TestEdgeCases:
    """Test edge cases and special scenarios"""
    
    def test_empty_object(self):
        """Test empty JSON object"""
        json_data = {}
        result = json_to_toon(json_data)
        assert result == "" or result == "{}"  # Empty object should produce empty string
    
    def test_special_characters_in_strings(self):
        """Test strings with special characters"""
        json_data = {
            "message": "Hello, World!",
            "quote": "He said: \"Hello\"",
            "path": "C:\\Users\\Documents",
            "unicode": "Café & Résumé"
        }
        result = json_to_toon(json_data)
        assert "message: Hello, World!" in result
        assert "quote: He said: \"Hello\"" in result
        assert "path: C:\\Users\\Documents" in result
        assert "unicode: Café & Résumé" in result
    
    def test_numeric_strings(self):
        """Test numeric strings vs actual numbers"""
        json_data = {
            "number": 123,
            "string_number": "123",
            "zipcode": "90210"
        }
        result = json_to_toon(json_data)
        assert "number: 123" in result
        assert "string_number: 123" in result
        assert "zipcode: 90210" in result
    
    def test_large_numbers(self):
        """Test large numbers"""
        json_data = {
            "big_int": 999999999999,
            "scientific": 1.5e10
        }
        result = json_to_toon(json_data)
        assert "big_int: 999999999999" in result
        # Scientific notation might be converted
        assert "scientific:" in result
    
    def test_negative_numbers(self):
        """Test negative numbers"""
        json_data = {
            "temperature": -10,
            "balance": -123.45
        }
        result = json_to_toon(json_data)
        assert "temperature: -10" in result
        assert "balance: -123.45" in result
    
    def test_keys_with_special_characters(self):
        """Test object keys with special characters"""
        json_data = {
            "key-with-dash": "value1",
            "key_with_underscore": "value2",
            "key.with.dot": "value3",
            "key with space": "value4"
        }
        result = json_to_toon(json_data)
        assert "key-with-dash: value1" in result
        assert "key_with_underscore: value2" in result
        assert "key.with.dot: value3" in result
        assert "key with space: value4" in result
    
    def test_numeric_keys(self):
        """Test numeric keys (though JSON doesn't support this, Python dicts can)"""
        json_data = {
            "1": "first",
            "2": "second"
        }
        result = json_to_toon(json_data)
        assert "1: first" in result
        assert "2: second" in result
    
    def test_very_long_strings(self):
        """Test very long string values"""
        long_string = "a" * 1000
        json_data = {"long_text": long_string}
        result = json_to_toon(json_data)
        assert f"long_text: {long_string}" == result
    
    def test_array_with_empty_objects(self):
        """Test array containing empty objects"""
        json_data = {
            "items": [{}, {"key": "value"}, {}]
        }
        result = json_to_toon(json_data)
        assert "items:" in result
        assert "[1]:" in result
        assert "  key: value" in result


class TestRootLevelTypes:
    """Test conversion when root is not an object"""
    
    def test_root_is_array(self):
        """Test when root element is an array"""
        json_data = [1, 2, 3]
        result = json_to_toon(json_data)
        assert "[0]: 1" in result
        assert "[1]: 2" in result
        assert "[2]: 3" in result
    
    def test_root_is_string(self):
        """Test when root element is a string"""
        json_data = "just a string"
        result = json_to_toon(json_data)
        assert result == "just a string"
    
    def test_root_is_number(self):
        """Test when root element is a number"""
        json_data = 42
        result = json_to_toon(json_data)
        assert result == "42"
    
    def test_root_is_boolean(self):
        """Test when root element is a boolean"""
        json_data = True
        result = json_to_toon(json_data)
        assert result == "True"
    
    def test_root_is_null(self):
        """Test when root element is null"""
        json_data = None
        result = json_to_toon(json_data)
        assert result == "None"


class TestIndentation:
    """Test indentation correctness"""
    
    def test_indentation_levels(self):
        """Test that indentation is correct at different levels"""
        json_data = {
            "level1": {
                "level2": {
                    "level3": "value"
                }
            }
        }
        result = json_to_toon(json_data)
        lines = result.split('\n')
        
        # Check indentation (2 spaces per level)
        assert "level1:" in lines[0]
        assert lines[0].startswith("level1:")
        assert "  level2:" in lines[1]
        assert lines[1].startswith("  level2:")
        assert "    level3: value" in lines[2]
        assert lines[2].startswith("    level3:")
    
    def test_mixed_indentation(self):
        """Test indentation with mixed arrays and objects"""
        json_data = {
            "items": [
                {
                    "nested": {
                        "deep": "value"
                    }
                }
            ]
        }
        result = json_to_toon(json_data)
        lines = result.split('\n')
        # Verify proper indentation structure
        assert any("items:" in line for line in lines)
        assert any("  [0]:" in line for line in lines)
        assert any("    nested:" in line for line in lines)
        assert any("      deep: value" in line for line in lines)


class TestOrdering:
    """Test key ordering (Python 3.7+ preserves insertion order)"""
    
    def test_key_order_preserved(self):
        """Test that key order is preserved"""
        json_data = {
            "first": 1,
            "second": 2,
            "third": 3
        }
        result = json_to_toon(json_data)
        lines = result.split('\n')
        # In Python 3.7+, dict order is preserved
        assert lines[0] == "first: 1"
        assert lines[1] == "second: 2"
        assert lines[2] == "third: 3"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
