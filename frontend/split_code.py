import re

with open("src/App.jsx", "r") as f:
    content = f.read()

# Replace synchronous imports with React.lazy
imports = [
    "Dashboard", "DepartmentManager", "ClassManager", "SubjectManager",
    "FacultyManager", "BatchManager", "FacultyMapping",
    "TimetableGenerator", "TimetableView", "Settings"
]

for component in imports:
    # Find the import line
    pattern = r"import " + component + r" from '([^']+)';"
    match = re.search(pattern, content)
    if match:
        path = match.group(1)
        # Replace the import line
        content = content.replace(match.group(0), f"const {component} = React.lazy(() => import('{path}'));")

# Add Suspense import if not exists
if "Suspense" not in content:
    content = content.replace("import React from 'react';", "import React, { Suspense } from 'react';")

# Wrap Routes with Suspense
suspense_wrapper = """
        <Suspense fallback={
            <div className="flex flex-col items-center justify-center h-screen space-y-4 bg-slate-50">
                <div className="w-12 h-12 border-4 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
                <div className="text-xl font-medium text-slate-500">Loading Application...</div>
            </div>
        }>
          <Routes>
"""
content = content.replace("<Routes>", suspense_wrapper)
content = content.replace("</Routes>", "  </Routes>\n        </Suspense>")

with open("src/App.jsx", "w") as f:
    f.write(content)

print("Code splitting implemented.")
