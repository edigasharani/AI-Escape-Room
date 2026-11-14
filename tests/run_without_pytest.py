import sys, traceback, importlib.util

spec = importlib.util.spec_from_file_location("t",__import__("os").path.join(__import__("os").path.dirname(__file__),"test_v2.py")); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
ok=fail=0
for n in sorted(dir(m)):
    if n.startswith("test_"):
        try: getattr(m,n)(); ok+=1; print("PASS",n)
        except Exception: fail+=1; print("FAIL",n); traceback.print_exc()
print(ok,"passed",fail,"failed")
