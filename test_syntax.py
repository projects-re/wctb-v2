import ast
try:
    with open('wctb_main.py') as f:
        ast.parse(f.read())
    print("Syntax OK")
except SyntaxError as e:
    print(f"Syntax Error at line {e.lineno}: {e.msg}")
