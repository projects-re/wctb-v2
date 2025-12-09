with open('wctb_main.py', 'r') as f:
    lines = f.readlines()[:821]

with open('wctb_main.py', 'w') as f:
    f.writelines(lines)

print(f"Fixed! Kept first 821 lines")
