import pathlib
p = pathlib.Path("/home/workspace/Scripts/health_check.py")
src = p.read_text()
src = src.replace("md = \"\\n\".join(lines)", "md = \"\\n\".join(str(x) for x in lines)")
p.write_text(src)
print("ok")
