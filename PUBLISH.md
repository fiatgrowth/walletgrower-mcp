# Publishing WalletGrower MCP Server v1.1.0

## What Needs to Happen

1. Upload package to PyPI (built, ready in `dist/`)
2. Create GitHub repo
3. Submit to MCP Registry via `mcp-publisher` CLI

The MCP Registry only stores metadata — it points to your PyPI package. It verifies ownership by checking for `<!-- mcp-name: com.walletgrower/financial-products -->` in the PyPI package README.

---

## Step 1: Upload to PyPI

The package is already built. From your local terminal (not the sandbox):

```bash
cd Walletgrower/agent-strategy/mcp/walletgrower-mcp
pip install twine
twine upload dist/* --username __token__ --password "YOUR_PYPI_API_TOKEN"
```

Or just run the publish script:
```bash
./publish.sh
```

Verify it's live: https://pypi.org/project/walletgrower-mcp/

---

## Step 2: Create GitHub Repo

```bash
cd walletgrower-mcp
git init
git add .
git commit -m "WalletGrower MCP server v1.1.0 — 17 tools across 4 financial verticals"
gh repo create fiatgrowth/walletgrower-mcp --public --source=. --push
```

---

## Step 3: Choose Authentication Method

### Option A: DNS auth → `com.walletgrower/financial-products` (recommended)

This gives you a branded namespace. Requires adding a DNS TXT record to walletgrower.com.

Check the MCP Registry docs for the exact TXT record value:
https://modelcontextprotocol.io/registry/authentication

```bash
mcp-publisher login dns
```

**No changes needed** — server.json and README already use `com.walletgrower/financial-products`.

### Option B: GitHub auth → `io.github.fiatgrowth/walletgrower` (faster)

No DNS setup required. But you must update two files:

1. `server.json` — change `name` to `io.github.fiatgrowth/walletgrower`
2. `README.md` — change `<!-- mcp-name: ... -->` to `<!-- mcp-name: io.github.fiatgrowth/walletgrower -->`
3. Re-upload to PyPI (the mcp-name tag must match in the PyPI package description)

```bash
mcp-publisher login github
```

---

## Step 4: Install mcp-publisher

```bash
# macOS/Linux
curl -L "https://github.com/modelcontextprotocol/registry/releases/latest/download/mcp-publisher_$(uname -s | tr '[:upper:]' '[:lower:]')_$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/').tar.gz" | tar xz mcp-publisher && sudo mv mcp-publisher /usr/local/bin/

# Or via Homebrew
brew install mcp-publisher

# Verify
mcp-publisher --help
```

---

## Step 5: Publish to MCP Registry

```bash
cd walletgrower-mcp
mcp-publisher publish
```

---

## Step 6: Verify

```bash
curl "https://registry.modelcontextprotocol.io/v0.1/servers?search=walletgrower"
```

---

## Files Reference

| File | Purpose |
|------|---------|
| `server.json` | MCP Registry metadata (name, version, packages) |
| `README.md` | Contains `<!-- mcp-name: ... -->` verification tag |
| `pyproject.toml` | PyPI package metadata |
| `dist/walletgrower_mcp-1.1.0-py3-none-any.whl` | Built wheel for PyPI |
| `dist/walletgrower_mcp-1.1.0.tar.gz` | Built sdist for PyPI |
| `publish.sh` | One-liner to upload to PyPI |

## Current Configuration

- **Server name:** `com.walletgrower/financial-products`
- **Version:** 1.1.0
- **PyPI package:** `walletgrower-mcp`
- **Auth method needed:** DNS (for `com.walletgrower/` namespace)
- **Tools:** 17 across 4 verticals (savings, credit cards, loans, budgeting apps)
