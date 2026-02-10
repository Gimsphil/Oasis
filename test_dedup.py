
def normalize(s):
    return s.replace(' ', '').replace('㎜', 'mm').lower()

def get_output_name(item_name, spec_name):
    norm_item = normalize(item_name)
    norm_spec = normalize(spec_name)
    
    if spec_name and norm_spec not in norm_item:
        return f"{item_name} {spec_name}".strip()
    else:
        return item_name.strip()

test_cases = [
    ("강제전선관 아연도 16 mm", "아연도 16㎜", "강제전선관 아연도 16 mm"),
    ("강제전선관 아연도", "16mm", "강제전선관 아연도 16mm"),
    ("매입콘센트 2구", "2구", "매입콘센트 2구"),
    ("HIV 2.5sq", "2.5sq", "HIV 2.5sq"),
    ("강제전선관", "아연도 16mm", "강제전선관 아연도 16mm"),
]

for item, spec, expected in test_cases:
    result = get_output_name(item, spec)
    print(f"Item: [{item}], Spec: [{spec}]")
    print(f"Result:   [{result}]")
    print(f"Expected: [{expected}]")
    print(f"Match: {result == expected}")
    print("-" * 20)
