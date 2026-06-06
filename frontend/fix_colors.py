import os
import re

directory = 'app/datasets'

replacements = {
    r'bg-zinc-950': 'bg-background',
    r'bg-zinc-900': 'bg-card',
    r'bg-zinc-800': 'bg-muted',
    r'border-zinc-800': 'border-border',
    r'border-zinc-700': 'border-border',
    r'text-zinc-100': 'text-foreground',
    r'text-zinc-300': 'text-foreground',
    r'text-zinc-400': 'text-muted-foreground',
    r'text-zinc-500': 'text-muted-foreground',
    r'text-zinc-900': 'text-primary-foreground',
    r'bg-zinc-100': 'bg-primary',
    r'hover:bg-zinc-800': 'hover:bg-accent',
    r'hover:bg-zinc-200': 'hover:bg-primary/90',
    r'hover:text-zinc-100': 'hover:text-accent-foreground',
    r'text-emerald-500': 'text-primary',
    r'text-emerald-400': 'text-primary',
    r'bg-emerald-600': 'bg-primary',
    r'bg-emerald-500/10': 'bg-primary/10',
    r'bg-emerald-500/20': 'bg-primary/20',
    r'bg-emerald-500': 'bg-primary',
    r'hover:bg-emerald-500': 'hover:bg-primary/90',
    r'hover:bg-emerald-600': 'hover:bg-primary/90',
    r'border-emerald-500': 'border-primary',
    r'border-emerald-500/20': 'border-primary/20',
    r'focus-visible:ring-emerald-500/50': 'focus-visible:ring-ring',
    r'focus-visible:ring-emerald-500': 'focus-visible:ring-ring',
    r'ring-emerald-500': 'ring-ring',
    r'border-zinc-900': 'border-border',
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
