# LuauShield

Correctness-first Roblox Luau obfuscation. Run with Python 3:

```bash
python server.py
```

Open `http://localhost:8000`. The default mode rewrites only quoted string
literals into a small Roblox-compatible decoder. It deliberately does not
rename identifiers or emulate code in a partial VM: those approaches can
change lexical scope, environment behavior, event callbacks, or unsupported
syntax. Invalid delimiters and unterminated strings are rejected before any
output is produced.

Run the regression suite with `python -m unittest -v`.