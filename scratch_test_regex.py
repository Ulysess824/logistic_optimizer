import re
html = '<p id="diesel-roi" class="text-lg font-black text-blue-700">206.1%</p>'
element_id = "diesel-roi"
value = "174.0%"
pattern = rf'(id="{element_id}"[^>]*>).*?(</)'
res = re.sub(pattern, rf'\g<1>{value}\g<2>', html, flags=re.DOTALL)
print(f"Original: {html}")
print(f"Result:   {res}")
