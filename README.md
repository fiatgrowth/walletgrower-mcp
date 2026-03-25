# WalletGrower MCP Server

Financial product comparison data for AI agents. Search, compare, and get personalized recommendations for high-yield savings accounts, credit cards, personal loans, budgeting apps, and 54 earning products across 11 categories.

<!-- mcp-name: com.walletgrower/financial-products -->

## What This Does

When your AI agent needs to answer questions like:

- "What savings account has the best APY?"
- "Find me a no-annual-fee credit card with cashback"
- "Best personal loan for debt consolidation with fair credit"
- "Compare SoFi vs Marcus personal loans"
- "What's the best free budgeting app?"
- "Compare YNAB vs Mint for couples"
- "Best survey apps that pay the most?"
- "What gig economy jobs don't require a car?"
- "Find passive income apps with no experience needed"

This MCP server gives your agent access to WalletGrower's curated, editorial-quality financial product data — the same data that powers [walletgrower.com](https://walletgrower.com).

## Tools Available

### Savings Accounts (8 products)
| Tool | Description |
|------|-------------|
| `search_savings_accounts` | Find accounts by APY, FDIC status, features |
| `get_savings_account` | Full details on a specific account |
| `compare_savings_accounts` | Side-by-side comparison |
| `recommend_savings_account` | Personalized pick based on goals |

### Credit Cards (8 products)
| Tool | Description |
|------|-------------|
| `search_credit_cards` | Filter by type, fees, rewards, credit score |
| `get_credit_card` | Full card details with APR, rewards, benefits |
| `compare_credit_cards` | Side-by-side card comparison |
| `recommend_credit_card` | Goal-based recommendation engine |

### Personal Loans (8 lenders)
| Tool | Description |
|------|-------------|
| `search_personal_loans` | Filter by APR, fees, funding speed, credit score |
| `get_personal_loan` | Full lender details with terms and requirements |
| `compare_personal_loans` | Side-by-side lender comparison |
| `recommend_personal_loan` | Goal-based loan recommendation |

### Budgeting & Savings Apps (8 products)
| Tool | Description |
|------|-------------|
| `search_budgeting_apps` | Filter by app type, pricing, features, platform |
| `get_budgeting_app` | Full app details with pricing and feature breakdown |
| `compare_budgeting_apps` | Side-by-side app comparison |
| `recommend_budgeting_app` | Goal-based recommendation engine |

### Earning Products (54 products across 11 categories)
| Tool | Description |
|------|-------------|
| `search_earning_products` | Filter by category, earnings, payout method, requirements |
| `get_earning_product` | Full details on a specific earning platform |
| `compare_earning_products` | Side-by-side platform comparison |
| `recommend_earning_product` | Goal-based recommendation (quick cash, passive income, etc.) |

### Discovery
| Tool | Description |
|------|-------------|
| `list_verticals` | See all available product categories |

**21 tools total** across 5 financial verticals.

## Installation

```bash
pip install walletgrower-mcp
```

## Usage

### Run as a standalone server

```bash
walletgrower-mcp
```

### Run with Python

```bash
python -m walletgrower_mcp
```

### Configure in Claude Desktop

Add to your Claude Desktop MCP config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "walletgrower": {
      "command": "walletgrower-mcp"
    }
  }
}
```

## Data Source

All product data is fetched live from the WalletGrower.com API (`walletgrower.com/wp-json/wg/v1/`), with a 5-minute in-memory cache. If the API is unreachable, the server falls back to bundled local data files.

Data is verified by the WalletGrower editorial team. APYs, rates, and fees are updated regularly.

## API Endpoints (for non-MCP consumers)

The same data is also available via REST API:

- `GET /wp-json/wg/v1/savings-accounts`
- `GET /wp-json/wg/v1/credit-cards`
- `GET /wp-json/wg/v1/personal-loans`
- `GET /wp-json/wg/v1/budgeting-apps`
- `GET /wp-json/wg/v1/earning-products`

Full API docs: [walletgrower.com/wp-json/wg/v1/](https://walletgrower.com/wp-json/wg/v1/)

## License

MIT — Fiat Growth, LLC
