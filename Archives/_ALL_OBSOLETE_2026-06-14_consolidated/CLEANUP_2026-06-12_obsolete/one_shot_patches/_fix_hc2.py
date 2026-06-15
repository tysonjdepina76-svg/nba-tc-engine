import json, sys
p = "/home/workspace/Scripts/health_check.py"
src = open(p).read()
src = src.replace("# Email the report", "# Save the report for the next agent to read
report_path = pathlib.Path("/home/workspace/Daily_Log/health_check_latest.json")
report_path.write_text(json.dumps({"fails": fails, "checks": [str(c) for c in checks], "ts": datetime.now(timezone.utc).isoformat()}, indent=2))
print(f"Report saved: {report_path}\n")
# Email the report")
open(p, "w").write(src)
print("ok")
