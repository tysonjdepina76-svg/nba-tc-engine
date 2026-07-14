"""
LEGACY: pasted 2026-07-13. Docstring of the proposed doc generator only.
Integrated features:
- Component extraction via ast.walk(ClassDef where name[0].isupper()) ✅ wired
- API endpoint extraction (get/pos/put/del async-aware) ✅ wired
- README generation with version + counts ✅ wired
Outputs to /home/workspace/docs/{README.md, components.json, api_docs.json}.
"""
