import os
def load_env_local(path=".env.local"):
    """Load KEY=VALUE pairs into os.environ without printing them."""
    if os.path.exists(path):
        for l in open(path):
            l = l.strip()
            if l and not l.startswith("#") and "=" in l:
                k, v = l.split("=", 1); os.environ.setdefault(k.strip(), v.strip().strip('"\''))
