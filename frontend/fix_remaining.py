import os
import re

directory = 'components/datasets'

replacements = {
    r'text-zinc-200': 'text-foreground',
    r'hover:text-zinc-200': 'hover:text-foreground',
    r'shadow-emerald-900/20': 'shadow-primary/20',
    r'hover:text-emerald-300': 'hover:text-primary/80',
    r'hover:bg-emerald-400/10': 'hover:bg-primary/10',
    r'text-white': 'text-primary-foreground', # assuming bg-primary is used with text-primary-foreground
}

for root, _, files in os.walk(directory):
    for file in files:
        if file.endswith('.tsx'):
            path = os.path.join(root, file)
            with open(path, 'r') as f:
                content = f.read()
            
            for pattern, replacement in replacements.items():
                content = re.sub(r'\b' + pattern + r'\b', replacement, content)
            
            with open(path, 'w') as f:
                f.write(content)

print("Done")
