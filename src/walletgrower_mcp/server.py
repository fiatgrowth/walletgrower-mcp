"""
WalletGrower MCP Server
========================
A Model Context Protocol server that exposes WalletGrower's financial product
data as tools for AI agents (Claude, GPT, Gemini, etc.).

This server fetches live data from the WalletGrower.com API — the same
structured product data that powers the website's comparison articles.

When registered in MCP directories, any AI agent can discover and use these
tools to answer their users' financial product questions.

Usage:
    pip install mcp httpx
    python walletgrower-mcp-server.py

MCP Tools Exposed:
    - search_savings_accounts    — Find savings accounts matching criteria
    - get_savings_account        — Get details on a specific product
    - compare_savings_accounts   — Side-by-side comparison
    - recommend_savings_account  — Personalized recommendation
    - search_credit_cards        — Find credit cards matching criteria
    - get_credit_card            — Get details on a specific credit card
    - compare_credit_cards       — Side-by-side credit card comparison
    - recommend_credit_card      — Personalized credit card recommendation
    - search_personal_loans      — Find personal loans matching criteria
    - get_personal_loan          — Get details on a specific personal loan
    - compare_personal_loans     — Side-by-side personal loan comparison
    - recommend_personal_loan    — Personalized personal loan recommendation
    - search_budgeting_apps      — Find budgeting apps matching criteria
    - get_budgeting_app          — Get details on a specific budgeting app
    - compare_budgeting_apps     — Side-by-side budgeting app comparison
    - recommend_budgeting_app    — Personalized budgeting app recommendation
    - search_earning_products    — Find earning products matching criteria
    - get_earning_product        — Get details on a specific earning product
    - compare_earning_products   — Side-by-side earning product comparison
    - recommend_earning_product  — Personalized earning product recommendation
    - list_verticals             — Show available product categories

This server is designed to be listed in:
    - Anthropic's MCP registry
    - OpenAI's plugin directory
    - Independent agent tool directories
"""

import json
import time
from pathlib import Path

import httpx
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
API_BASE = "https://walletgrower.com/wp-json/wg/v1"
CACHE_TTL_SECONDS = 300  # 5 min cache — rates don't change mid-conversation
LOCAL_FALLBACK_DIR = Path(__file__).parent.parent / "data"

# Simple in-memory cache
_cache: dict[str, dict] = {}


def _fetch_products(category: str = "savings-accounts") -> dict:
    """
    Fetch product data from the live WalletGrower API with caching.
    Falls back to local JSON files if the API is unreachable.
    """
    cache_key = category
    now = time.time()

    # Return cached data if fresh
    if cache_key in _cache and (now - _cache[cache_key]["ts"]) < CACHE_TTL_SECONDS:
        return _cache[cache_key]["data"]

    # Try live API
    try:
        resp = httpx.get(f"{API_BASE}/{category}", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        _cache[cache_key] = {"data": data, "ts": now}
        return data
    except Exception:
        pass

    # Fallback to local file
    local_file = LOCAL_FALLBACK_DIR / f"{category}.json"
    if local_file.exists():
        with open(local_file, "r") as f:
            data = json.load(f)
        _cache[cache_key] = {"data": data, "ts": now}
        return data

    return {"products": [], "api_version": "1.0.0", "source": "WalletGrower.com"}


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "WalletGrower",
    description=(
        "Financial product comparison data for AI agents. "
        "Search, compare, and get recommendations for high-yield savings accounts, "
        "credit cards, personal loans, budgeting apps, earning products, and more. "
        "21 tools across 5 verticals powered by WalletGrower.com editorial data."
    ),
)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def search_savings_accounts(
    min_apy: float | None = None,
    fdic_insured: bool | None = None,
    needs_mobile_app: bool | None = None,
    needs_joint_account: bool | None = None,
    max_results: int = 5,
) -> str:
    """
    Search for high-yield savings accounts matching specific criteria.

    Use this when a user asks questions like:
    - "What savings accounts have the best APY?"
    - "Find me an FDIC-insured savings account with a mobile app"
    - "Which savings accounts support joint accounts?"

    Args:
        min_apy: Minimum annual percentage yield (e.g., 4.0 for 4.0%)
        fdic_insured: Only show FDIC-insured accounts
        needs_mobile_app: Only show accounts with a mobile app
        needs_joint_account: Only show accounts supporting joint holders
        max_results: Maximum number of results (1-10, default 5)

    Returns:
        JSON string with matching savings accounts sorted by APY (highest first)
    """
    data = _fetch_products("savings-accounts")
    products = data.get("products", [])

    if min_apy is not None:
        products = [p for p in products if p["apy"]["base_rate"] >= min_apy]
    if fdic_insured is not None:
        products = [p for p in products if p["insurance"]["fdic_insured"] == fdic_insured]
    if needs_mobile_app is not None:
        products = [p for p in products if p["features"].get("mobile_app") == needs_mobile_app]
    if needs_joint_account is not None:
        products = [p for p in products if p["features"].get("joint_accounts") == needs_joint_account]

    products.sort(key=lambda p: -p["apy"]["base_rate"])
    products = products[:max_results]

    results = []
    for p in products:
        results.append({
            "product_id": p["product_id"],
            "institution": p["institution"]["name"],
            "product_name": p["product_name"],
            "apy": f"{p['apy']['base_rate']}%",
            "max_apy": f"{p['apy'].get('max_rate', p['apy']['base_rate'])}%",
            "monthly_fee": f"${p['fees']['monthly_fee']}",
            "fdic_insured": p["insurance"]["fdic_insured"],
            "mobile_app": p["features"].get("mobile_app", False),
            "walletgrower_score": f"{p['ratings']['walletgrower_score']}/5",
            "verdict": p["ratings"]["walletgrower_verdict"],
            "best_for": p["ratings"]["best_for"],
            "cta_text": p.get("affiliate", {}).get("cta_text", ""),
            "article_url": p.get("metadata", {}).get("walletgrower_article_url", ""),
        })

    return json.dumps({
        "results": results,
        "total_found": len(results),
        "data_source": "walletgrower.com/wp-json/wg/v1/savings-accounts",
        "source": "WalletGrower.com",
        "disclaimer": "APYs are variable and subject to change. Data verified by WalletGrower editorial team. Not financial advice.",
    }, indent=2)


@mcp.tool()
def get_savings_account(product_id: str) -> str:
    """
    Get detailed information about a specific savings account.

    Use this when a user asks about a specific bank or product, like:
    - "Tell me about the SoFi savings account"
    - "What's the APY on Marcus by Goldman Sachs?"
    - "What are the pros and cons of Ally's savings account?"

    Args:
        product_id: The product identifier (e.g., 'sofi-savings', 'ally-hysa', 'marcus-hysa')

    Returns:
        JSON string with full product details including APY, fees, features, pros/cons
    """
    data = _fetch_products("savings-accounts")
    for p in data.get("products", []):
        if p["product_id"] == product_id:
            result = {
                "institution": p["institution"]["name"],
                "product_name": p["product_name"],
                "website": p["institution"]["website"],
                "apy": {
                    "rate": f"{p['apy']['base_rate']}%",
                    "max_rate": f"{p['apy'].get('max_rate', p['apy']['base_rate'])}%",
                    "variable": p["apy"]["is_variable"],
                    "promo_rate": p["apy"].get("promo_rate"),
                    "verified_date": p["apy"]["rate_as_of"],
                },
                "fees": {
                    "monthly": f"${p['fees']['monthly_fee']}",
                    "wire_transfer": f"${p['fees'].get('wire_transfer_fee', 0)}",
                },
                "requirements": {
                    "min_opening_deposit": f"${p['requirements']['min_opening_deposit']}",
                    "min_balance_for_apy": f"${p['requirements']['min_balance_to_earn_apy']}",
                },
                "features": p["features"],
                "insurance": {
                    "fdic": p["insurance"]["fdic_insured"],
                    "coverage": f"${p['insurance']['insurance_limit']:,}",
                },
                "ratings": {
                    "walletgrower_score": f"{p['ratings']['walletgrower_score']}/5",
                    "verdict": p["ratings"]["walletgrower_verdict"],
                    "pros": p["ratings"]["pros"],
                    "cons": p["ratings"]["cons"],
                    "best_for": p["ratings"]["best_for"],
                },
                "source": "WalletGrower.com",
                "article": p.get("metadata", {}).get("walletgrower_article_url"),
            }
            return json.dumps(result, indent=2)

    return json.dumps({"error": f"Product '{product_id}' not found. Use search_savings_accounts to find available products."})


@mcp.tool()
def compare_savings_accounts(product_ids: str) -> str:
    """
    Compare multiple savings accounts side-by-side.

    Use this when a user wants to choose between specific options, like:
    - "Compare SoFi vs Ally savings accounts"
    - "Which is better, Marcus or Discover savings?"
    - "Show me SoFi, Ally, and Varo side by side"

    Args:
        product_ids: Comma-separated product IDs (e.g., 'sofi-savings,ally-hysa,marcus-hysa')

    Returns:
        JSON string with side-by-side comparison including a recommendation
    """
    ids = [pid.strip() for pid in product_ids.split(",")]
    data = _fetch_products("savings-accounts")
    products_by_id = {p["product_id"]: p for p in data.get("products", [])}

    compared = []
    not_found = []
    for pid in ids:
        if pid in products_by_id:
            p = products_by_id[pid]
            compared.append({
                "product_id": pid,
                "institution": p["institution"]["name"],
                "apy": p["apy"]["base_rate"],
                "monthly_fee": p["fees"]["monthly_fee"],
                "mobile_app": p["features"].get("mobile_app", False),
                "atm_access": p["features"].get("atm_access", False),
                "joint_accounts": p["features"].get("joint_accounts", False),
                "walletgrower_score": p["ratings"]["walletgrower_score"],
                "pros": p["ratings"]["pros"][:3],
                "cons": p["ratings"]["cons"][:2],
                "best_for": p["ratings"]["best_for"],
            })
        else:
            not_found.append(pid)

    if not compared:
        return json.dumps({"error": "No matching products found. Use search_savings_accounts to find available product IDs."})

    best_apy = max(compared, key=lambda x: x["apy"])
    best_rated = max(compared, key=lambda x: x["walletgrower_score"])

    result = {
        "comparison": compared,
        "highlights": {
            "highest_apy": f"{best_apy['institution']} ({best_apy['apy']}%)",
            "highest_rated": f"{best_rated['institution']} ({best_rated['walletgrower_score']}/5)",
        },
        "source": "WalletGrower.com",
    }
    if not_found:
        result["not_found"] = not_found

    return json.dumps(result, indent=2)


@mcp.tool()
def recommend_savings_account(
    goal: str = "general",
    balance_amount: float | None = None,
    needs_mobile_app: bool = False,
    needs_atm_access: bool = False,
) -> str:
    """
    Get a personalized savings account recommendation based on the user's needs.

    Use this when a user asks for advice, like:
    - "Where should I put my emergency fund?"
    - "What's the best savings account for $50,000?"
    - "I need a savings account with ATM access and a good app"

    Args:
        goal: The user's savings goal. One of:
              'emergency_fund' — quick access, no withdrawal limits
              'highest_rate' — maximum APY above all else
              'all_in_one' — checking + savings + ATM in one place
              'high_balance' — best for large deposits ($25k+)
              'simple' — lowest friction, easiest to open
              'general' — balanced recommendation
        balance_amount: Expected deposit amount in USD (helps optimize for tiers)
        needs_mobile_app: Whether the user requires a mobile app
        needs_atm_access: Whether the user needs ATM access

    Returns:
        JSON string with top recommendation, reasoning, and alternatives
    """
    data = _fetch_products("savings-accounts")
    products = data.get("products", [])

    scored = []
    for p in products:
        score = p["ratings"]["walletgrower_score"] * 10 + p["apy"]["base_rate"] * 5
        reasons = []

        if goal == "highest_rate":
            score += p["apy"]["base_rate"] * 20
            reasons.append(f"{p['apy']['base_rate']}% APY")
        elif goal == "emergency_fund":
            if not p["features"].get("withdrawal_limit"):
                score += 15
                reasons.append("No withdrawal limits — access anytime")
            if p["features"].get("mobile_app"):
                score += 10
                reasons.append("Mobile app for quick access")
        elif goal == "all_in_one":
            if p["features"].get("linked_checking"):
                score += 20
                reasons.append("Linked checking account")
            if p["features"].get("atm_access"):
                score += 15
                reasons.append("ATM access")
        elif goal == "high_balance":
            if not p["apy"].get("tiers"):
                score += 15
                reasons.append("Flat rate — no balance caps on APY")
        elif goal == "simple":
            if p["requirements"]["min_opening_deposit"] == 0:
                score += 10
                reasons.append("No minimum deposit")
            if p["fees"]["monthly_fee"] == 0:
                score += 10

        if needs_mobile_app and not p["features"].get("mobile_app"):
            score -= 100
        if needs_atm_access and not p["features"].get("atm_access"):
            score -= 100

        scored.append({
            "product_id": p["product_id"],
            "institution": p["institution"]["name"],
            "apy": f"{p['apy']['base_rate']}%",
            "score": round(score, 1),
            "verdict": p["ratings"]["walletgrower_verdict"],
            "reasons": reasons or ["Well-rounded option"],
            "best_for": p["ratings"]["best_for"],
        })

    scored.sort(key=lambda x: -x["score"])

    return json.dumps({
        "goal": goal,
        "top_recommendation": scored[0] if scored else None,
        "runner_up": scored[1] if len(scored) > 1 else None,
        "also_consider": scored[2] if len(scored) > 2 else None,
        "source": "WalletGrower.com",
        "disclaimer": "APYs are variable and subject to change. Data verified by WalletGrower editorial team. Not financial advice.",
    }, indent=2)


# ---------------------------------------------------------------------------
# Credit Card Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def search_credit_cards(
    card_type: str | None = None,
    no_annual_fee: bool | None = None,
    no_foreign_fee: bool | None = None,
    min_bonus_value: float | None = None,
    has_intro_apr: bool | None = None,
    network: str | None = None,
    rewards_type: str | None = None,
    credit_score: str | None = None,
    max_results: int = 5,
) -> str:
    """
    Search for credit cards matching specific criteria.

    Use this when a user asks questions like:
    - "What are the best cashback credit cards?"
    - "Find me a no-annual-fee card with travel rewards"
    - "What credit cards have 0% intro APR?"
    - "Best credit card for bad credit"

    Args:
        card_type: Filter by type: 'cashback', 'travel', 'secured', 'balance_transfer', 'student'
        no_annual_fee: Only show cards with $0 annual fee
        no_foreign_fee: Only show cards with no foreign transaction fees
        min_bonus_value: Minimum sign-up bonus value in USD (e.g., 200)
        has_intro_apr: Only show cards with a 0% intro APR offer
        network: Card network: 'visa', 'mastercard', 'amex', 'discover'
        rewards_type: Rewards program type: 'cashback', 'points', 'miles'
        credit_score: Required credit score level: 'excellent', 'good', 'fair', 'poor'
        max_results: Maximum number of results (1-10, default 5)

    Returns:
        JSON string with matching credit cards sorted by WalletGrower score
    """
    data = _fetch_products("credit-cards")
    products = data.get("products", [])

    if card_type:
        products = [p for p in products if p["card_type"] == card_type]
    if no_annual_fee is True:
        products = [p for p in products if p["fees"]["annual_fee"] == 0]
    if no_foreign_fee is True:
        products = [p for p in products if p["fees"]["foreign_transaction_fee"] == 0]
    if min_bonus_value is not None:
        products = [p for p in products if (p.get("sign_up_bonus", {}).get("value_usd") or 0) >= min_bonus_value]
    if has_intro_apr is True:
        products = [p for p in products if p["apr"].get("intro_purchase_apr") == 0 or p["apr"].get("intro_bt_apr") == 0]
    if network:
        products = [p for p in products if p["issuer"]["network"] == network]
    if rewards_type:
        products = [p for p in products if p["rewards"]["rewards_type"] == rewards_type]
    if credit_score:
        products = [p for p in products if p["requirements"]["credit_score_min"] == credit_score]

    products.sort(key=lambda p: -p["ratings"]["walletgrower_score"])
    products = products[:max_results]

    results = []
    for p in products:
        results.append({
            "product_id": p["product_id"],
            "issuer": p["issuer"]["name"],
            "card_name": p["card_name"],
            "card_type": p["card_type"],
            "annual_fee": f"${p['fees']['annual_fee']}",
            "rewards": p["rewards"]["base_earn_rate"],
            "sign_up_bonus": p.get("sign_up_bonus", {}).get("offer", "None"),
            "intro_apr": f"{p['apr'].get('intro_purchase_apr', 'N/A')}% for {p['apr'].get('intro_purchase_duration_months', 'N/A')} months" if p["apr"].get("intro_purchase_apr") == 0 else "None",
            "walletgrower_score": f"{p['ratings']['walletgrower_score']}/5",
            "verdict": p["ratings"]["walletgrower_verdict"],
            "best_for": p["ratings"]["best_for"],
            "cta_text": p.get("affiliate", {}).get("cta_text", ""),
            "article_url": p.get("metadata", {}).get("walletgrower_article_url", ""),
        })

    return json.dumps({
        "results": results,
        "total_found": len(results),
        "data_source": "walletgrower.com/wp-json/wg/v1/credit-cards",
        "source": "WalletGrower.com",
        "disclaimer": "Rates and fees are subject to change. Data verified by WalletGrower editorial team. Not financial advice.",
    }, indent=2)


@mcp.tool()
def get_credit_card(product_id: str) -> str:
    """
    Get detailed information about a specific credit card.

    Use this when a user asks about a specific card, like:
    - "Tell me about the Chase Sapphire Preferred"
    - "What's the annual fee on the Amex Blue Cash Preferred?"
    - "What are the pros and cons of the Capital One Quicksilver?"

    Args:
        product_id: The product identifier (e.g., 'chase-sapphire-preferred', 'capital-one-quicksilver')

    Returns:
        JSON string with full card details including APR, fees, rewards, benefits, pros/cons
    """
    data = _fetch_products("credit-cards")
    for p in data.get("products", []):
        if p["product_id"] == product_id:
            result = {
                "issuer": p["issuer"]["name"],
                "card_name": p["card_name"],
                "card_type": p["card_type"],
                "website": p["issuer"]["website"],
                "annual_fee": f"${p['fees']['annual_fee']}",
                "apr": {
                    "range": f"{p['apr']['min_apr']}%–{p['apr']['max_apr']}%",
                    "variable": p["apr"]["is_variable"],
                    "intro_purchase_apr": p["apr"].get("intro_purchase_apr"),
                    "intro_purchase_duration": p["apr"].get("intro_purchase_duration_months"),
                    "intro_bt_apr": p["apr"].get("intro_bt_apr"),
                    "intro_bt_duration": p["apr"].get("intro_bt_duration_months"),
                },
                "rewards": {
                    "type": p["rewards"]["rewards_type"],
                    "base_earn_rate": p["rewards"]["base_earn_rate"],
                    "bonus_categories": p["rewards"].get("bonus_categories", []),
                    "sign_up_bonus": p.get("sign_up_bonus", {}).get("offer", "None"),
                    "sign_up_bonus_value": f"${p.get('sign_up_bonus', {}).get('value_usd', 0)}",
                },
                "fees": {
                    "annual": f"${p['fees']['annual_fee']}",
                    "foreign_transaction": f"{p['fees']['foreign_transaction_fee']}%",
                    "late_payment": f"${p['fees']['late_payment_fee']}",
                },
                "requirements": {
                    "credit_score": p["requirements"]["credit_score_min"],
                    "credit_range": p["requirements"]["credit_score_range"],
                },
                "benefits": p.get("benefits", []),
                "ratings": {
                    "walletgrower_score": f"{p['ratings']['walletgrower_score']}/5",
                    "verdict": p["ratings"]["walletgrower_verdict"],
                    "pros": p["ratings"]["pros"],
                    "cons": p["ratings"]["cons"],
                    "best_for": p["ratings"]["best_for"],
                },
                "source": "WalletGrower.com",
                "article": p.get("metadata", {}).get("walletgrower_article_url"),
            }
            return json.dumps(result, indent=2)

    return json.dumps({"error": f"Card '{product_id}' not found. Use search_credit_cards to find available cards."})


@mcp.tool()
def compare_credit_cards(product_ids: str) -> str:
    """
    Compare multiple credit cards side-by-side.

    Use this when a user wants to choose between specific cards, like:
    - "Compare Chase Sapphire Preferred vs Amex Platinum"
    - "Which cashback card is better, Capital One or Chase Freedom?"
    - "Show me three travel cards side by side"

    Args:
        product_ids: Comma-separated product IDs (e.g., 'chase-sapphire-preferred,amex-platinum')

    Returns:
        JSON string with side-by-side comparison including highlights
    """
    ids = [pid.strip() for pid in product_ids.split(",")]
    data = _fetch_products("credit-cards")
    products_by_id = {p["product_id"]: p for p in data.get("products", [])}

    compared = []
    not_found = []
    for pid in ids:
        if pid in products_by_id:
            p = products_by_id[pid]
            compared.append({
                "product_id": pid,
                "issuer": p["issuer"]["name"],
                "card_name": p["card_name"],
                "card_type": p["card_type"],
                "annual_fee": p["fees"]["annual_fee"],
                "rewards_type": p["rewards"]["rewards_type"],
                "base_earn_rate": p["rewards"]["base_earn_rate"],
                "sign_up_bonus": p.get("sign_up_bonus", {}).get("value_usd", 0),
                "intro_apr": p["apr"].get("intro_purchase_apr"),
                "walletgrower_score": p["ratings"]["walletgrower_score"],
                "pros": p["ratings"]["pros"][:3],
                "cons": p["ratings"]["cons"][:2],
                "best_for": p["ratings"]["best_for"],
            })
        else:
            not_found.append(pid)

    if not compared:
        return json.dumps({"error": "No matching cards found. Use search_credit_cards to find available card IDs."})

    lowest_fee = min(compared, key=lambda x: x["annual_fee"])
    highest_bonus = max(compared, key=lambda x: x["sign_up_bonus"])
    best_rated = max(compared, key=lambda x: x["walletgrower_score"])

    result = {
        "comparison": compared,
        "highlights": {
            "lowest_annual_fee": f"{lowest_fee['card_name']} (${lowest_fee['annual_fee']})" if lowest_fee["annual_fee"] > 0 else f"{lowest_fee['card_name']} (No annual fee)",
            "highest_sign_up_bonus": f"{highest_bonus['card_name']} (${highest_bonus['sign_up_bonus']})",
            "highest_rated": f"{best_rated['card_name']} ({best_rated['walletgrower_score']}/5)",
        },
        "source": "WalletGrower.com",
    }
    if not_found:
        result["not_found"] = not_found

    return json.dumps(result, indent=2)


@mcp.tool()
def recommend_credit_card(goal: str = "general") -> str:
    """
    Get a personalized credit card recommendation based on the user's needs.

    Use this when a user asks for advice, like:
    - "What credit card should I get?"
    - "Best card for travel rewards"
    - "I want to earn cashback on groceries"
    - "Best credit card for building credit"

    Args:
        goal: The user's primary goal. One of:
              'highest_cashback' — maximize cashback rewards
              'travel_rewards' — accumulate points/miles for travel
              'balance_transfer' — lowest APR for debt transfer
              'no_annual_fee' — eliminate card costs
              'sign_up_bonus' — maximize upfront bonus value
              'building_credit' — secured card or credit-builder
              'general' — balanced recommendation

    Returns:
        JSON string with top recommendation, reasoning, and alternatives
    """
    data = _fetch_products("credit-cards")
    products = data.get("products", [])

    scored = []
    for p in products:
        score = p["ratings"]["walletgrower_score"] * 10
        reasons = []

        if goal == "highest_cashback":
            if p["rewards"]["rewards_type"] == "cashback":
                score += 20
                reasons.append(f"Flat {p['rewards']['base_earn_rate']} cashback")
            if p["fees"]["annual_fee"] == 0:
                score += 10
                reasons.append("No annual fee to eat into cashback")
        elif goal == "travel_rewards":
            if p["rewards"]["rewards_type"] in ["points", "miles"]:
                score += 20
                reasons.append(f"Earns {p['rewards']['rewards_type']}")
            if "travel" in p.get("benefits", []):
                score += 10
        elif goal == "balance_transfer":
            if p["apr"].get("intro_bt_apr") == 0:
                score += 25
                reasons.append(f"{p['apr'].get('intro_bt_duration_months')}mo 0% intro BT APR")
        elif goal == "no_annual_fee":
            if p["fees"]["annual_fee"] == 0:
                score += 30
                reasons.append("$0 annual fee")
        elif goal == "sign_up_bonus":
            bonus_val = p.get("sign_up_bonus", {}).get("value_usd", 0)
            score += bonus_val / 10
            if bonus_val > 0:
                reasons.append(f"${bonus_val} sign-up bonus")
        elif goal == "building_credit":
            if p["card_type"] == "secured":
                score += 25
                reasons.append("Secured card — builds credit for beginners")
            if p["requirements"]["credit_score_min"] == "poor":
                score += 15
                reasons.append("Accepts poor credit")

        scored.append({
            "product_id": p["product_id"],
            "issuer": p["issuer"]["name"],
            "card_name": p["card_name"],
            "annual_fee": f"${p['fees']['annual_fee']}" if p["fees"]["annual_fee"] > 0 else "No annual fee",
            "rewards": p["rewards"]["base_earn_rate"],
            "sign_up_bonus": f"${p.get('sign_up_bonus', {}).get('value_usd', 0)}",
            "score": round(score, 1),
            "verdict": p["ratings"]["walletgrower_verdict"],
            "reasons": reasons[:4] or ["Well-rounded option"],
            "best_for": p["ratings"]["best_for"],
        })

    scored.sort(key=lambda x: -x["score"])

    return json.dumps({
        "goal": goal,
        "top_recommendation": scored[0] if scored else None,
        "runner_up": scored[1] if len(scored) > 1 else None,
        "also_consider": scored[2] if len(scored) > 2 else None,
        "source": "WalletGrower.com",
        "disclaimer": "Rates and benefits are subject to change. Data verified by WalletGrower editorial team. Not financial advice.",
    }, indent=2)


# ---------------------------------------------------------------------------
# Personal Loan Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def search_personal_loans(
    loan_type: str | None = None,
    min_amount: float | None = None,
    max_amount: float | None = None,
    max_apr: float | None = None,
    credit_score: str | None = None,
    prequalification: bool | None = None,
    same_day_funding: bool | None = None,
    direct_pay: bool | None = None,
    max_results: int = 5,
) -> str:
    """
    Search for personal loans matching specific criteria.

    Use this when a user asks questions like:
    - "Best personal loan for debt consolidation"
    - "What personal loans have same-day funding?"
    - "Find loans with no origination fees"
    - "Personal loans for fair credit"

    Args:
        loan_type: Filter by type: 'debt_consolidation', 'personal', 'home_improvement', 'major_purchase'
        min_amount: Minimum loan amount in USD
        max_amount: Maximum loan amount in USD
        max_apr: Maximum APR threshold
        credit_score: Credit level: 'excellent', 'good', 'fair', 'poor'
        prequalification: Only show loans with prequalification available
        same_day_funding: Only show loans with same-day funding
        direct_pay: Only show loans with direct creditor payment
        max_results: Maximum number of results (1-10, default 5)

    Returns:
        JSON string with matching personal loans sorted by WalletGrower score
    """
    data = _fetch_products("personal-loans")
    products = data.get("products", [])

    score_order = {"poor": 0, "fair": 1, "good": 2, "excellent": 3}

    if loan_type:
        products = [p for p in products if p["loan_type"] == loan_type]
    if min_amount is not None:
        products = [p for p in products if p["loan_amounts"]["max_amount"] >= min_amount]
    if max_amount is not None:
        products = [p for p in products if p["loan_amounts"]["min_amount"] <= max_amount]
    if max_apr is not None:
        products = [p for p in products if p["apr"]["min_apr"] <= max_apr]
    if prequalification is True:
        products = [p for p in products if p["features"].get("prequalification_available") is True]
    if same_day_funding is True:
        products = [p for p in products if p["features"].get("same_day_funding") is True]
    if credit_score:
        user_level = score_order.get(credit_score, 2)
        products = [p for p in products if score_order.get(p["requirements"]["credit_score_min"], 2) <= user_level]
    if direct_pay is True:
        products = [p for p in products if p["features"].get("direct_pay_to_creditors") is True]

    products.sort(key=lambda p: -p["ratings"]["walletgrower_score"])
    products = products[:max_results]

    results = []
    for p in products:
        results.append({
            "product_id": p["product_id"],
            "lender": p["lender"]["name"],
            "loan_name": p["loan_name"],
            "loan_type": p["loan_type"],
            "apr_range": f"{p['apr']['min_apr']}%–{p['apr']['max_apr']}%",
            "loan_amounts": f"${p['loan_amounts']['min_amount']:,}–${p['loan_amounts']['max_amount']:,}",
            "origination_fee": p["fees"]["origination_fee"],
            "prepayment_penalty": p["fees"]["prepayment_penalty"],
            "same_day_funding": p["features"].get("same_day_funding", False),
            "prequalification": p["features"].get("prequalification_available", False),
            "direct_pay": p["features"].get("direct_pay_to_creditors", False),
            "walletgrower_score": f"{p['ratings']['walletgrower_score']}/5",
            "verdict": p["ratings"]["walletgrower_verdict"],
            "best_for": p["ratings"]["best_for"],
            "cta_text": p.get("affiliate", {}).get("cta_text", ""),
            "article_url": p.get("metadata", {}).get("walletgrower_article_url", ""),
        })

    return json.dumps({
        "results": results,
        "total_found": len(results),
        "data_source": "walletgrower.com/wp-json/wg/v1/personal-loans",
        "source": "WalletGrower.com",
        "disclaimer": "Rates and fees are subject to change. Data verified by WalletGrower editorial team. Not financial advice.",
    }, indent=2)


@mcp.tool()
def get_personal_loan(product_id: str) -> str:
    """
    Get detailed information about a specific personal loan product.

    Use this when a user asks about a specific lender, like:
    - "Tell me about the SoFi personal loan"
    - "What's the APR range on Marcus personal loans?"
    - "What are the pros and cons of Upstart?"
    - "Does LightStream charge an origination fee?"

    Args:
        product_id: The product identifier (e.g., 'sofi-personal-loan', 'marcus-personal-loan', 'upstart-personal-loan')

    Returns:
        JSON string with full loan details including APR, fees, requirements, features, pros/cons
    """
    data = _fetch_products("personal-loans")
    for p in data.get("products", []):
        if p["product_id"] == product_id:
            result = {
                "lender": p["lender"]["name"],
                "lender_type": p["lender"]["type"],
                "loan_name": p["loan_name"],
                "loan_type": p["loan_type"],
                "website": p["lender"]["website"],
                "apr": {
                    "range": f"{p['apr']['min_apr']}%–{p['apr']['max_apr']}%",
                    "fixed": p["apr"]["is_fixed"],
                    "autopay_discount": p["apr"].get("autopay_discount"),
                    "verified_date": p["apr"]["rate_as_of"],
                },
                "loan_amounts": {
                    "min": f"${p['loan_amounts']['min_amount']:,}",
                    "max": f"${p['loan_amounts']['max_amount']:,}",
                },
                "loan_terms": {
                    "min_months": p["loan_terms"]["min_months"],
                    "max_months": p["loan_terms"]["max_months"],
                    "available_terms": p["loan_terms"]["available_terms"],
                },
                "fees": {
                    "origination": p["fees"]["origination_fee"],
                    "late_payment": f"${p['fees']['late_payment_fee']}",
                    "prepayment_penalty": p["fees"]["prepayment_penalty"],
                },
                "requirements": {
                    "credit_score": p["requirements"]["credit_score_min"],
                    "credit_range": p["requirements"]["credit_score_range"],
                    "min_income": f"${p['requirements']['min_income']:,}" if p["requirements"].get("min_income") else "Not disclosed",
                    "employment_required": p["requirements"]["employment_required"],
                    "cosigner_allowed": p["requirements"]["cosigner_allowed"],
                },
                "features": {
                    "direct_pay_to_creditors": p["features"].get("direct_pay_to_creditors", False),
                    "unemployment_protection": p["features"].get("unemployment_protection", False),
                    "prequalification": p["features"].get("prequalification_available", False),
                    "same_day_funding": p["features"].get("same_day_funding", False),
                    "joint_application": p["features"].get("joint_application", False),
                    "mobile_app": p["features"].get("mobile_app", False),
                    "loan_uses": p["features"].get("loan_uses", []),
                },
                "ratings": {
                    "walletgrower_score": f"{p['ratings']['walletgrower_score']}/5",
                    "verdict": p["ratings"]["walletgrower_verdict"],
                    "pros": p["ratings"]["pros"],
                    "cons": p["ratings"]["cons"],
                    "best_for": p["ratings"]["best_for"],
                },
                "source": "WalletGrower.com",
                "article": p.get("metadata", {}).get("walletgrower_article_url"),
            }
            return json.dumps(result, indent=2)

    return json.dumps({"error": f"Product '{product_id}' not found. Use search_personal_loans to find available products."})


@mcp.tool()
def compare_personal_loans(product_ids: str) -> str:
    """
    Compare multiple personal loans side-by-side.

    Use this when a user wants to choose between specific lenders, like:
    - "Compare SoFi vs Marcus personal loans"
    - "Which is better for debt consolidation, Discover or Happy Money?"
    - "Show me SoFi, LightStream, and Upstart side by side"

    Args:
        product_ids: Comma-separated product IDs (e.g., 'sofi-personal-loan,marcus-personal-loan')

    Returns:
        JSON string with side-by-side comparison including a recommendation
    """
    ids = [pid.strip() for pid in product_ids.split(",")]
    data = _fetch_products("personal-loans")
    products_by_id = {p["product_id"]: p for p in data.get("products", [])}

    compared = []
    not_found = []
    for pid in ids:
        if pid in products_by_id:
            p = products_by_id[pid]
            compared.append({
                "product_id": pid,
                "lender": p["lender"]["name"],
                "loan_type": p["loan_type"],
                "apr_range": f"{p['apr']['min_apr']}%–{p['apr']['max_apr']}%",
                "min_apr": p["apr"]["min_apr"],
                "loan_amounts": f"${p['loan_amounts']['min_amount']:,}–${p['loan_amounts']['max_amount']:,}",
                "max_amount": p["loan_amounts"]["max_amount"],
                "origination_fee": p["fees"]["origination_fee"],
                "prepayment_penalty": p["fees"]["prepayment_penalty"],
                "same_day_funding": p["features"].get("same_day_funding", False),
                "direct_pay": p["features"].get("direct_pay_to_creditors", False),
                "prequalification": p["features"].get("prequalification_available", False),
                "credit_score_min": p["requirements"]["credit_score_min"],
                "walletgrower_score": p["ratings"]["walletgrower_score"],
                "pros": p["ratings"]["pros"][:3],
                "cons": p["ratings"]["cons"][:2],
                "best_for": p["ratings"]["best_for"],
            })
        else:
            not_found.append(pid)

    if not compared:
        return json.dumps({"error": "No matching products found. Use search_personal_loans to find available product IDs."})

    lowest_apr = min(compared, key=lambda x: x["min_apr"])
    best_rated = max(compared, key=lambda x: x["walletgrower_score"])
    highest_amount = max(compared, key=lambda x: x["max_amount"])

    result = {
        "comparison": compared,
        "highlights": {
            "lowest_starting_apr": f"{lowest_apr['lender']} ({lowest_apr['apr_range']})",
            "highest_rated": f"{best_rated['lender']} ({best_rated['walletgrower_score']}/5)",
            "highest_loan_amount": f"{highest_amount['lender']} (up to ${highest_amount['max_amount']:,})",
        },
        "source": "WalletGrower.com",
    }
    if not_found:
        result["not_found"] = not_found

    return json.dumps(result, indent=2)


@mcp.tool()
def recommend_personal_loan(
    goal: str = "general",
    loan_amount: float | None = None,
    credit_score: str = "good",
    needs_fast_funding: bool = False,
    needs_direct_pay: bool = False,
    wants_no_fees: bool = False,
) -> str:
    """
    Get a personalized personal loan recommendation based on the user's needs.

    Use this when a user asks for advice, like:
    - "What's the best personal loan for me?"
    - "I need a $20,000 loan for debt consolidation"
    - "Best personal loan for someone with fair credit"
    - "I need same-day funding on a personal loan"

    Args:
        goal: The user's primary goal. One of:
              'debt_consolidation' — pay off credit cards or other debt
              'lowest_rate' — minimize interest paid
              'fast_funding' — get money as quickly as possible
              'large_loan' — need a high loan amount ($50k+)
              'fair_credit' — best options for fair or limited credit
              'no_fees' — minimize origination and other fees
              'general' — balanced recommendation
        loan_amount: Desired loan amount in USD
        credit_score: Credit level: 'excellent', 'good', 'fair', 'poor'
        needs_fast_funding: Whether the user needs same-day or next-day funding
        needs_direct_pay: Whether the user wants direct creditor payment
        wants_no_fees: Whether the user wants to avoid origination fees

    Returns:
        JSON string with top recommendation, reasoning, and alternatives
    """
    data = _fetch_products("personal-loans")
    products = data.get("products", [])

    score_order = {"poor": 0, "fair": 1, "good": 2, "excellent": 3}
    user_level = score_order.get(credit_score, 2)

    scored = []
    for p in products:
        # Credit score gate
        card_min = score_order.get(p["requirements"]["credit_score_min"], 2)
        if user_level < card_min:
            continue

        score = p["ratings"]["walletgrower_score"] * 10
        reasons = []

        if goal == "debt_consolidation":
            if p["features"].get("direct_pay_to_creditors"):
                score += 20
                reasons.append("Direct pay to creditors")
            if p["loan_type"] == "debt_consolidation":
                score += 15
                reasons.append("Purpose-built for debt consolidation")
        elif goal == "lowest_rate":
            score += (35 - p["apr"]["min_apr"]) * 2
            reasons.append(f"Starting APR of {p['apr']['min_apr']}%")
            if p["apr"].get("autopay_discount"):
                score += 5
                reasons.append(f"{p['apr']['autopay_discount']}% autopay discount")
        elif goal == "fast_funding":
            if p["features"].get("same_day_funding"):
                score += 30
                reasons.append("Same-day funding available")
        elif goal == "large_loan":
            if p["loan_amounts"]["max_amount"] >= 100000:
                score += 25
                reasons.append(f"Loans up to ${p['loan_amounts']['max_amount']:,}")
        elif goal == "fair_credit":
            if p["requirements"]["credit_score_min"] == "fair":
                score += 20
                reasons.append("Accepts fair credit")
            if p["loan_amounts"]["min_amount"] <= 2000:
                score += 5
                reasons.append(f"Low minimum of ${p['loan_amounts']['min_amount']:,}")
        elif goal == "no_fees":
            if p["fees"].get("origination_fee") == "0%" or p["fees"].get("origination_fee_max_pct") in (None, 0):
                score += 25
                reasons.append("No origination fee")
            if p["fees"]["late_payment_fee"] == 0:
                score += 10
                reasons.append("No late payment fee")

        # Loan amount fit
        if loan_amount:
            if p["loan_amounts"]["min_amount"] <= loan_amount <= p["loan_amounts"]["max_amount"]:
                score += 10
            else:
                score -= 50

        # Preference modifiers
        if needs_fast_funding and not p["features"].get("same_day_funding"):
            score -= 30
        if needs_direct_pay and not p["features"].get("direct_pay_to_creditors"):
            score -= 30
        if wants_no_fees:
            fee_pct = p["fees"].get("origination_fee_max_pct") or 0
            score -= fee_pct * 5

        scored.append({
            "product_id": p["product_id"],
            "lender": p["lender"]["name"],
            "loan_name": p["loan_name"],
            "apr_range": f"{p['apr']['min_apr']}%–{p['apr']['max_apr']}%",
            "loan_amounts": f"${p['loan_amounts']['min_amount']:,}–${p['loan_amounts']['max_amount']:,}",
            "origination_fee": p["fees"]["origination_fee"],
            "score": round(score, 1),
            "verdict": p["ratings"]["walletgrower_verdict"],
            "reasons": reasons[:4] or ["Well-rounded option"],
            "best_for": p["ratings"]["best_for"],
        })

    scored.sort(key=lambda x: -x["score"])

    return json.dumps({
        "goal": goal,
        "credit_score": credit_score,
        "loan_amount": loan_amount,
        "top_recommendation": scored[0] if scored else None,
        "runner_up": scored[1] if len(scored) > 1 else None,
        "also_consider": scored[2] if len(scored) > 2 else None,
        "source": "WalletGrower.com",
        "disclaimer": "Rates and fees are subject to change. Data verified by WalletGrower editorial team. Not financial advice.",
    }, indent=2)


# ---------------------------------------------------------------------------
# Budgeting Apps Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def search_budgeting_apps(
    app_type: str | None = None,
    has_free_tier: bool | None = None,
    max_monthly_cost: float | None = None,
    has_credit_score: bool | None = None,
    has_auto_savings: bool | None = None,
    has_cash_advance: bool | None = None,
    has_budget_tracking: bool | None = None,
    has_investment: bool | None = None,
    has_bill_negotiation: bool | None = None,
    platform: str | None = None,
    limit: int = 5,
) -> str:
    """
    Search for budgeting and savings apps matching specific criteria.

    Use this when a user asks questions like:
    - "What are the best budgeting apps?"
    - "Find me a budgeting app with auto-savings and credit monitoring"
    - "Best free budgeting apps"
    - "Budgeting apps that offer cash advances"
    - "Apps for tracking subscriptions and negotiating bills"

    Args:
        app_type: Filter by type: 'budgeting', 'savings', 'credit_monitoring', 'cashback', 'all_in_one', 'debt_payoff', 'investing_micro'
        has_free_tier: Only show apps with a free tier
        max_monthly_cost: Maximum monthly cost in USD (filters premium plans)
        has_credit_score: Only show apps with credit score monitoring
        has_auto_savings: Only show apps with automatic savings features
        has_cash_advance: Only show apps offering cash advances
        has_budget_tracking: Only show apps with budget tracking
        has_investment: Only show apps with investment features
        has_bill_negotiation: Only show apps with bill negotiation
        platform: Filter by platform: 'ios', 'android', 'web'
        limit: Maximum number of results (1-10, default 5)

    Returns:
        JSON string with matching budgeting apps sorted by WalletGrower score
    """
    data = _fetch_products("budgeting-apps")
    products = data.get("products", [])

    if app_type:
        products = [p for p in products if p["app_type"] == app_type]
    if has_free_tier is not None:
        products = [p for p in products if p["pricing"]["has_free_tier"] == has_free_tier]
    if max_monthly_cost is not None:
        products = [p for p in products if p["pricing"]["monthly_cost"] <= max_monthly_cost]
    if has_credit_score is not None:
        products = [p for p in products if p["features"].get("credit_score_monitoring") == has_credit_score]
    if has_auto_savings is not None:
        products = [p for p in products if p["features"].get("auto_savings") == has_auto_savings]
    if has_cash_advance is not None:
        products = [p for p in products if p["features"].get("cash_advance") == has_cash_advance]
    if has_budget_tracking is not None:
        products = [p for p in products if p["features"].get("budget_tracking") == has_budget_tracking]
    if has_investment is not None:
        products = [p for p in products if p["features"].get("investment_features") == has_investment]
    if has_bill_negotiation is not None:
        products = [p for p in products if p["features"].get("bill_negotiation") == has_bill_negotiation]
    if platform:
        products = [p for p in products if p["platforms"].get(platform) is True]

    products.sort(key=lambda p: -p["ratings"]["walletgrower_score"])
    products = products[:limit]

    results = []
    for p in products:
        results.append({
            "product_id": p["product_id"],
            "company": p["company"]["name"],
            "app_name": p["app_name"],
            "app_type": p["app_type"],
            "pricing_model": p["pricing"]["pricing_model"],
            "monthly_cost": f"${p['pricing']['monthly_cost']}" if p["pricing"]["monthly_cost"] > 0 else "Free",
            "has_free_tier": p["pricing"]["has_free_tier"],
            "credit_score": p["features"].get("credit_score_monitoring", False),
            "auto_savings": p["features"].get("auto_savings", False),
            "bill_negotiation": p["features"].get("bill_negotiation", False),
            "cash_advance": p["features"].get("cash_advance", False),
            "budget_tracking": p["features"].get("budget_tracking", False),
            "platforms": [k for k, v in p["platforms"].items() if v is True],
            "walletgrower_score": f"{p['ratings']['walletgrower_score']}/5",
            "verdict": p["ratings"]["walletgrower_verdict"],
            "best_for": p["ratings"]["best_for"],
            "cta_text": p.get("affiliate", {}).get("cta_text", ""),
            "article_url": p.get("metadata", {}).get("walletgrower_article_url", ""),
        })

    return json.dumps({
        "results": results,
        "total_found": len(results),
        "data_source": "walletgrower.com/wp-json/wg/v1/budgeting-apps",
        "source": "WalletGrower.com",
        "disclaimer": "Features and pricing are subject to change. Data verified by WalletGrower editorial team. Not financial advice.",
    }, indent=2)


@mcp.tool()
def get_budgeting_app(product_id: str) -> str:
    """
    Get detailed information about a specific budgeting or savings app.

    Use this when a user asks about a specific app, like:
    - "Tell me about YNAB"
    - "What are the features of Mint?"
    - "What's the pros and cons of Rocket Money?"
    - "Does Albert offer cash advances?"

    Args:
        product_id: The product identifier (e.g., 'ynab', 'mint-intuit', 'albert-savings', 'credit-sesame')

    Returns:
        JSON string with full app details including features, pricing, ratings, pros/cons
    """
    data = _fetch_products("budgeting-apps")
    for p in data.get("products", []):
        if p["product_id"] == product_id:
            result = {
                "company": p["company"]["name"],
                "company_type": p["company"]["type"],
                "app_name": p["app_name"],
                "app_type": p["app_type"],
                "website": p["company"]["website"],
                "logo_url": p["company"].get("logo_url"),
                "pricing": {
                    "model": p["pricing"]["pricing_model"],
                    "has_free_tier": p["pricing"]["has_free_tier"],
                    "free_tier_description": p["pricing"].get("free_tier_description"),
                    "monthly_cost": p["pricing"]["monthly_cost"],
                    "annual_cost": p["pricing"].get("annual_cost"),
                    "trial_days": p["pricing"].get("trial_days"),
                },
                "features": {
                    "budget_tracking": p["features"].get("budget_tracking", False),
                    "auto_savings": p["features"].get("auto_savings", False),
                    "bill_negotiation": p["features"].get("bill_negotiation", False),
                    "credit_score_monitoring": p["features"].get("credit_score_monitoring", False),
                    "credit_score_provider": p["features"].get("credit_score_provider"),
                    "cashback_rewards": p["features"].get("cashback_rewards", False),
                    "investment_features": p["features"].get("investment_features", False),
                    "debt_tracking": p["features"].get("debt_tracking", False),
                    "cash_advance": p["features"].get("cash_advance", False),
                    "cash_advance_limit": p["features"].get("cash_advance_limit"),
                    "spending_insights": p["features"].get("spending_insights", False),
                    "savings_goals": p["features"].get("savings_goals", False),
                    "joint_accounts": p["features"].get("joint_accounts", False),
                    "custom_categories": p["features"].get("custom_categories", False),
                    "recurring_detection": p["features"].get("recurring_transaction_detection", False),
                },
                "platforms": {
                    "ios": p["platforms"].get("ios", False),
                    "android": p["platforms"].get("android", False),
                    "web": p["platforms"].get("web", False),
                },
                "security": {
                    "bank_level_encryption": p["security"].get("bank_level_encryption", False),
                    "two_factor_auth": p["security"].get("two_factor_auth", False),
                    "fdic_insured": p["security"].get("fdic_insured", False),
                    "fdic_partner_bank": p["security"].get("fdic_partner_bank"),
                    "read_only_bank_access": p["security"].get("read_only_bank_access", False),
                },
                "ratings": {
                    "walletgrower_score": f"{p['ratings']['walletgrower_score']}/5",
                    "verdict": p["ratings"]["walletgrower_verdict"],
                    "app_store_rating": p["ratings"].get("app_store_rating"),
                    "google_play_rating": p["ratings"].get("google_play_rating"),
                    "pros": p["ratings"]["pros"],
                    "cons": p["ratings"]["cons"],
                    "best_for": p["ratings"]["best_for"],
                },
                "source": "WalletGrower.com",
                "article": p.get("metadata", {}).get("walletgrower_article_url"),
            }
            return json.dumps(result, indent=2)

    return json.dumps({"error": f"App '{product_id}' not found. Use search_budgeting_apps to find available apps."})


@mcp.tool()
def compare_budgeting_apps(product_ids: str) -> str:
    """
    Compare multiple budgeting apps side-by-side.

    Use this when a user wants to choose between specific apps, like:
    - "Compare YNAB vs Mint vs Rocket Money"
    - "Which is better for couples, YNAB or Goodbudget?"
    - "Show me Albert vs Credit Sesame side by side"

    Args:
        product_ids: Comma-separated product IDs (e.g., 'ynab,mint-intuit,rocket-money')

    Returns:
        JSON string with side-by-side comparison including highlights
    """
    ids = [pid.strip() for pid in product_ids.split(",")]
    data = _fetch_products("budgeting-apps")
    products_by_id = {p["product_id"]: p for p in data.get("products", [])}

    compared = []
    not_found = []
    for pid in ids:
        if pid in products_by_id:
            p = products_by_id[pid]
            compared.append({
                "product_id": pid,
                "app_name": p["app_name"],
                "company": p["company"]["name"],
                "app_type": p["app_type"],
                "pricing": f"${p['pricing']['monthly_cost']}/mo" if p["pricing"]["monthly_cost"] > 0 else "Free",
                "monthly_cost": p["pricing"]["monthly_cost"],
                "has_free_tier": p["pricing"]["has_free_tier"],
                "budget_tracking": p["features"].get("budget_tracking", False),
                "auto_savings": p["features"].get("auto_savings", False),
                "credit_monitoring": p["features"].get("credit_score_monitoring", False),
                "cash_advance": p["features"].get("cash_advance", False),
                "bill_negotiation": p["features"].get("bill_negotiation", False),
                "investment": p["features"].get("investment_features", False),
                "platforms": [k for k, v in p["platforms"].items() if v is True],
                "walletgrower_score": p["ratings"]["walletgrower_score"],
                "pros": p["ratings"]["pros"][:3],
                "cons": p["ratings"]["cons"][:2],
                "best_for": p["ratings"]["best_for"],
            })
        else:
            not_found.append(pid)

    if not compared:
        return json.dumps({"error": "No matching apps found. Use search_budgeting_apps to find available app IDs."})

    lowest_cost = min(compared, key=lambda x: x["monthly_cost"])
    best_rated = max(compared, key=lambda x: x["walletgrower_score"])
    most_features = max(compared, key=lambda x: sum([
        x["budget_tracking"],
        x["auto_savings"],
        x["credit_monitoring"],
        x["cash_advance"],
        x["bill_negotiation"],
        x["investment"],
    ]))

    result = {
        "comparison": compared,
        "highlights": {
            "lowest_cost": f"{lowest_cost['app_name']} ({lowest_cost['pricing']})" if lowest_cost["monthly_cost"] > 0 else f"{lowest_cost['app_name']} (Free)",
            "highest_rated": f"{best_rated['app_name']} ({best_rated['walletgrower_score']}/5)",
            "most_features": most_features["app_name"],
        },
        "source": "WalletGrower.com",
    }
    if not_found:
        result["not_found"] = not_found

    return json.dumps(result, indent=2)


@mcp.tool()
def recommend_budgeting_app(goal: str = "budget_beginner") -> str:
    """
    Get a personalized budgeting app recommendation based on the user's needs.

    Use this when a user asks for advice, like:
    - "What budgeting app should I use?"
    - "Best app for couples managing money together"
    - "I want to save money without changing my habits"
    - "Best app for building credit"
    - "Recommend a free budgeting app"

    Args:
        goal: The user's primary goal. One of:
              'budget_beginner' — easy, free budgeting to get started
              'serious_budgeter' — comprehensive budgeting for those willing to learn
              'credit_building' — focus on credit monitoring and improvement
              'save_money' — automatic savings and cutting expenses
              'earn_cashback' — earn rewards and cashback on purchases
              'couples' — shared accounts and joint budgeting
              'free_only' — completely free with no premium option

    Returns:
        JSON string with top recommendation, reasoning, and alternatives
    """
    data = _fetch_products("budgeting-apps")
    products = data.get("products", [])

    scored = []
    for p in products:
        score = p["ratings"]["walletgrower_score"] * 10
        reasons = []

        if goal == "budget_beginner":
            if p["pricing"]["has_free_tier"]:
                score += 20
                reasons.append("Free to get started")
            if p["features"].get("budget_tracking"):
                score += 10
        elif goal == "serious_budgeter":
            if not p["pricing"]["has_free_tier"] or p["pricing"]["monthly_cost"] > 0:
                score += 15
                reasons.append("Premium features worth paying for")
            if p["features"].get("custom_categories"):
                score += 10
                reasons.append("Custom categories for detail")
        elif goal == "credit_building":
            if p["features"].get("credit_score_monitoring"):
                score += 25
                reasons.append("Monitors credit score")
            if p["features"].get("debt_tracking"):
                score += 10
                reasons.append("Tracks debt progress")
        elif goal == "save_money":
            if p["features"].get("auto_savings"):
                score += 25
                reasons.append("Automatic savings without effort")
            if p["features"].get("spending_insights"):
                score += 10
                reasons.append("Identifies spending to cut")
        elif goal == "earn_cashback":
            if p["features"].get("cashback_rewards"):
                score += 25
                reasons.append("Earn rewards on purchases")
        elif goal == "couples":
            if p["features"].get("joint_accounts"):
                score += 25
                reasons.append("Joint account management")
        elif goal == "free_only":
            if p["pricing"]["has_free_tier"] and p["pricing"]["monthly_cost"] == 0:
                score += 30
                reasons.append("Completely free")
            else:
                score = -100

        scored.append({
            "product_id": p["product_id"],
            "app_name": p["app_name"],
            "company": p["company"]["name"],
            "pricing": f"${p['pricing']['monthly_cost']}/mo" if p["pricing"]["monthly_cost"] > 0 else "Free",
            "score": round(score, 1),
            "verdict": p["ratings"]["walletgrower_verdict"],
            "reasons": reasons[:4] or ["Well-rounded option"],
            "best_for": p["ratings"]["best_for"],
        })

    scored.sort(key=lambda x: -x["score"])

    return json.dumps({
        "goal": goal,
        "top_recommendation": scored[0] if scored else None,
        "runner_up": scored[1] if len(scored) > 1 else None,
        "also_consider": scored[2] if len(scored) > 2 else None,
        "source": "WalletGrower.com",
        "disclaimer": "Features and pricing are subject to change. Data verified by WalletGrower editorial team. Not financial advice.",
    }, indent=2)


# ---------------------------------------------------------------------------
# Earning Products Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def search_earning_products(
    category: str | None = None,
    tags: str | None = None,
    min_monthly_earning: float | None = None,
    max_monthly_earning: float | None = None,
    payout_method: str | None = None,
    payout_frequency: str | None = None,
    country: str = "US",
    vehicle_required: bool | None = None,
    has_signup_bonus: bool | None = None,
    min_score: float | None = None,
    limit: int = 10,
) -> str:
    """
    Search for earning products matching specific criteria.

    Use this when a user asks questions like:
    - "What are the best survey apps to make money?"
    - "Find me gig economy jobs that pay daily"
    - "Which apps have passive income and PayPal payouts?"
    - "Best earning apps for students"

    Args:
        category: Filter by category: 'surveys', 'receipt-cashback', 'offer-walls', 'games', 'gig-economy', 'job-boards', 'cashback-shopping', 'earned-wage-access', 'freelancing', 'passive-income', 'referral-bonuses'
        tags: Comma-separated tags to filter (e.g., 'no-experience-needed,work-from-home')
        min_monthly_earning: Minimum estimated monthly earning in USD
        max_monthly_earning: Maximum estimated monthly earning in USD
        payout_method: Filter by payout: 'paypal', 'direct-deposit', 'gift-card', 'venmo', 'cash-app', 'check', 'crypto', 'bank-transfer', 'prepaid-card'
        payout_frequency: Filter by frequency: 'instant', 'daily', 'weekly', 'bi-weekly', 'monthly', 'on-demand'
        country: ISO 2-letter country code (default 'US')
        vehicle_required: Only show apps requiring a vehicle
        has_signup_bonus: Only show products with sign-up bonuses
        min_score: Minimum WalletGrower score (0-10)
        limit: Maximum number of results (1-25, default 10)

    Returns:
        JSON string with matching earning products sorted by estimated monthly earning
    """
    data = _fetch_products("earning-products")
    products = data.get("products", [])

    if category:
        products = [p for p in products if p["category"] == category]
    if tags:
        tag_list = [t.strip() for t in tags.split(",")]
        products = [p for p in products if any(t in p.get("tags", []) for t in tag_list)]
    if min_monthly_earning is not None:
        products = [p for p in products if p["earning_model"].get("estimated_monthly_high", 0) >= min_monthly_earning]
    if max_monthly_earning is not None:
        products = [p for p in products if p["earning_model"].get("estimated_monthly_low", 0) <= max_monthly_earning]
    if payout_method:
        products = [p for p in products if payout_method.lower().replace("-", " ").title() in p["payout"]["methods"] or payout_method.lower() in [m.lower() for m in p["payout"]["methods"]]]
    if payout_frequency:
        products = [p for p in products if payout_frequency.lower() in p["payout"]["payout_frequency"].lower()]
    if country:
        products = [p for p in products if country in p["requirements"]["countries"]]
    if vehicle_required is not None:
        products = [p for p in products if p["requirements"]["vehicle_required"] == vehicle_required]
    if has_signup_bonus is not None:
        products = [p for p in products if bool(p["earning_model"].get("signup_bonus")) == has_signup_bonus]
    if min_score is not None:
        products = [p for p in products if p["ratings"]["walletgrower_score"] >= min_score]

    products.sort(key=lambda p: -p["earning_model"].get("estimated_monthly_high", 0))
    products = products[:limit]

    results = []
    for p in products:
        results.append({
            "product_id": p["product_id"],
            "company": p["company"]["name"],
            "product_name": p["product_name"],
            "category": p["category"],
            "estimated_monthly": f"${p['earning_model'].get('estimated_monthly_low', 0)}–${p['earning_model'].get('estimated_monthly_high', 0)}",
            "estimated_hourly": f"${p['earning_model'].get('estimated_hourly_low', 0)}–${p['earning_model'].get('estimated_hourly_high', 0)}/hr" if p["earning_model"].get("estimated_hourly_high") else "Varies",
            "payout_methods": p["payout"]["methods"],
            "payout_frequency": p["payout"]["payout_frequency"],
            "min_payout": f"${p['payout']['minimum_threshold']}",
            "signup_bonus": f"${p['earning_model'].get('signup_bonus', {}).get('amount', 0)}" if p["earning_model"].get("signup_bonus") else "None",
            "time_to_first_payout": p["earning_model"].get("time_to_first_payout", "N/A"),
            "walletgrower_score": f"{p['ratings']['walletgrower_score']}/5",
            "best_for": p["ratings"].get("best_for", ""),
            "cta_text": p.get("affiliate", {}).get("cta_text", ""),
            "article_url": p.get("metadata", {}).get("walletgrower_article_url", ""),
        })

    return json.dumps({
        "results": results,
        "total_found": len(results),
        "data_source": "walletgrower.com/wp-json/wg/v1/earning-products",
        "source": "WalletGrower.com",
        "disclaimer": "Earning estimates are based on user reports and may vary. Data verified by WalletGrower editorial team. Not guaranteed earnings.",
    }, indent=2)


@mcp.tool()
def get_earning_product(product_id: str) -> str:
    """
    Get detailed information about a specific earning product.

    Use this when a user asks about a specific app, like:
    - "Tell me about Swagbucks"
    - "How much can I earn on InboxDollars?"
    - "What are the pros and cons of DoorDash?"
    - "Is Cashapp app safe for side income?"

    Args:
        product_id: The product identifier (e.g., 'swagbucks', 'inboxdollars', 'doordash', 'uber-eats')

    Returns:
        JSON string with full product details including earning potential, payouts, requirements, pros/cons
    """
    data = _fetch_products("earning-products")
    for p in data.get("products", []):
        if p["product_id"] == product_id:
            result = {
                "company": p["company"]["name"],
                "product_name": p["product_name"],
                "category": p["category"],
                "secondary_categories": p.get("secondary_categories", []),
                "website": p["company"]["website"],
                "app_stores": {
                    "ios": p["company"].get("app_store_url"),
                    "android": p["company"].get("play_store_url"),
                },
                "earning": {
                    "type": p["earning_model"]["type"],
                    "monthly_range": f"${p['earning_model'].get('estimated_monthly_low', 0)}–${p['earning_model'].get('estimated_monthly_high', 0)}",
                    "hourly_range": f"${p['earning_model'].get('estimated_hourly_low', 0)}–${p['earning_model'].get('estimated_hourly_high', 0)}/hr" if p["earning_model"].get("estimated_hourly_high") else "Varies",
                    "details": p["earning_model"].get("earning_details", ""),
                    "signup_bonus": p["earning_model"].get("signup_bonus"),
                    "time_to_first_payout": p["earning_model"].get("time_to_first_payout"),
                },
                "payout": {
                    "methods": p["payout"]["methods"],
                    "minimum_threshold": f"${p['payout']['minimum_threshold']}",
                    "frequency": p["payout"]["payout_frequency"],
                },
                "requirements": {
                    "minimum_age": p["requirements"]["minimum_age"],
                    "countries": p["requirements"]["countries"],
                    "device": p["requirements"]["device"],
                    "vehicle_required": p["requirements"]["vehicle_required"],
                    "background_check": p["requirements"]["background_check"],
                    "special_skills": p["requirements"]["special_skills"],
                    "startup_cost": f"${p['requirements']['startup_cost']}",
                },
                "ratings": {
                    "walletgrower_score": f"{p['ratings']['walletgrower_score']}/5",
                    "app_store_rating": p["ratings"].get("app_store_rating"),
                    "play_store_rating": p["ratings"].get("play_store_rating"),
                    "trustpilot_rating": p["ratings"].get("trustpilot_rating"),
                    "bbb_rating": p["ratings"].get("bbb_rating"),
                    "pros": p["ratings"]["pros"],
                    "cons": p["ratings"]["cons"],
                    "best_for": p["ratings"].get("best_for", ""),
                },
                "tags": p.get("tags", []),
                "source": "WalletGrower.com",
                "article": p.get("metadata", {}).get("walletgrower_article_url"),
            }
            return json.dumps(result, indent=2)

    return json.dumps({"error": f"Product '{product_id}' not found. Use search_earning_products to find available products."})


@mcp.tool()
def compare_earning_products(product_ids: str) -> str:
    """
    Compare multiple earning products side-by-side.

    Use this when a user wants to choose between specific apps, like:
    - "Compare Swagbucks vs InboxDollars vs Survey Junkie"
    - "Which gig app pays more, DoorDash or Uber Eats?"
    - "Show me the top 3 cashback shopping apps side by side"

    Args:
        product_ids: Comma-separated product IDs (e.g., 'swagbucks,inboxdollars,survey-junkie')

    Returns:
        JSON string with side-by-side comparison highlighting highest earning, highest rated, and lowest payout threshold
    """
    ids = [pid.strip() for pid in product_ids.split(",")]
    data = _fetch_products("earning-products")
    products_by_id = {p["product_id"]: p for p in data.get("products", [])}

    compared = []
    not_found = []
    for pid in ids:
        if pid in products_by_id:
            p = products_by_id[pid]
            compared.append({
                "product_id": pid,
                "company": p["company"]["name"],
                "product_name": p["product_name"],
                "category": p["category"],
                "estimated_monthly": f"${p['earning_model'].get('estimated_monthly_low', 0)}–${p['earning_model'].get('estimated_monthly_high', 0)}",
                "monthly_high": p["earning_model"].get("estimated_monthly_high", 0),
                "payout_methods": p["payout"]["methods"],
                "min_payout": p["payout"]["minimum_threshold"],
                "payout_frequency": p["payout"]["payout_frequency"],
                "signup_bonus": f"${p['earning_model'].get('signup_bonus', {}).get('amount', 0)}" if p["earning_model"].get("signup_bonus") else "None",
                "vehicle_required": p["requirements"]["vehicle_required"],
                "walletgrower_score": p["ratings"]["walletgrower_score"],
                "pros": p["ratings"]["pros"][:3],
                "cons": p["ratings"]["cons"][:2],
                "best_for": p["ratings"].get("best_for", ""),
            })
        else:
            not_found.append(pid)

    if not compared:
        return json.dumps({"error": "No matching products found. Use search_earning_products to find available product IDs."})

    highest_earning = max(compared, key=lambda x: x["monthly_high"])
    best_rated = max(compared, key=lambda x: x["walletgrower_score"])
    lowest_payout = min(compared, key=lambda x: x["min_payout"])

    result = {
        "comparison": compared,
        "highlights": {
            "highest_earning_potential": f"{highest_earning['product_name']} ({highest_earning['estimated_monthly']})",
            "highest_rated": f"{best_rated['product_name']} ({best_rated['walletgrower_score']}/5)",
            "lowest_payout_threshold": f"{lowest_payout['product_name']} (${lowest_payout['min_payout']})",
        },
        "source": "WalletGrower.com",
    }
    if not_found:
        result["not_found"] = not_found

    return json.dumps(result, indent=2)


@mcp.tool()
def recommend_earning_product(goal: str = "side_income") -> str:
    """
    Get a personalized earning product recommendation based on the user's goals.

    Use this when a user asks for advice, like:
    - "How can I make quick cash?"
    - "What's the best passive income app?"
    - "Best earning app for students"
    - "I want to earn money without experience"
    - "What gig work pays best?"

    Args:
        goal: The user's primary goal. One of:
              'quick_cash' — earn money as fast as possible
              'highest_earning' — maximize potential monthly earnings
              'passive_income' — earn with minimal ongoing effort
              'work_from_home' — apps you can do from your couch
              'no_experience' — no special skills or experience required
              'student_friendly' — flexible around class schedule
              'gig_worker' — structured gig economy/delivery apps
              'side_income' — balanced option for side hustle

    Returns:
        JSON string with top recommendation, reasoning, and alternatives
    """
    data = _fetch_products("earning-products")
    products = data.get("products", [])

    scored = []
    for p in products:
        score = p["ratings"]["walletgrower_score"] * 10
        reasons = []

        if goal == "quick_cash":
            if "instant" in p["payout"]["payout_frequency"].lower():
                score += 25
                reasons.append("Instant payouts available")
            if p["payout"]["minimum_threshold"] <= 5:
                score += 15
                reasons.append("Low minimum threshold")
        elif goal == "highest_earning":
            score += p["earning_model"].get("estimated_monthly_high", 0) / 10
            reasons.append(f"Up to ${p['earning_model'].get('estimated_monthly_high', 0)}/month")
        elif goal == "passive_income":
            if "passive" in p.get("tags", []) or "passive-income" in p.get("secondary_categories", []):
                score += 30
                reasons.append("Passive earning possible")
            if p["earning_model"].get("estimated_hourly_high", 0) == 0:
                score += 15
                reasons.append("No hourly time commitment")
        elif goal == "work_from_home":
            if "work-from-home" in p.get("tags", []):
                score += 25
                reasons.append("100% work-from-home eligible")
            if not p["requirements"]["vehicle_required"]:
                score += 10
                reasons.append("No vehicle needed")
        elif goal == "no_experience":
            if "no-experience-needed" in p.get("tags", []):
                score += 25
                reasons.append("No experience or skills required")
            if not p["requirements"]["special_skills"]:
                score += 10
        elif goal == "student_friendly":
            if "student-friendly" in p.get("tags", []) or "flexible-schedule" in p.get("tags", []):
                score += 25
                reasons.append("Flexible schedule for students")
            if p["earning_model"].get("estimated_monthly_high", 0) >= 50:
                score += 10
                reasons.append("Decent earning potential")
        elif goal == "gig_worker":
            if p["category"] == "gig-economy":
                score += 30
                reasons.append("Purpose-built gig platform")
            if p["earning_model"].get("estimated_monthly_high", 0) >= 500:
                score += 15
        elif goal == "side_income":
            score += (p["earning_model"].get("estimated_monthly_high", 0) / 5)
            if "flexible-schedule" in p.get("tags", []):
                score += 10
                reasons.append("Flexible for side work")

        scored.append({
            "product_id": p["product_id"],
            "company": p["company"]["name"],
            "product_name": p["product_name"],
            "category": p["category"],
            "estimated_monthly": f"${p['earning_model'].get('estimated_monthly_low', 0)}–${p['earning_model'].get('estimated_monthly_high', 0)}",
            "score": round(score, 1),
            "payout_frequency": p["payout"]["payout_frequency"],
            "reasons": reasons[:4] or ["Good option for your needs"],
            "best_for": p["ratings"].get("best_for", ""),
        })

    scored.sort(key=lambda x: -x["score"])

    return json.dumps({
        "goal": goal,
        "top_recommendation": scored[0] if scored else None,
        "runner_up": scored[1] if len(scored) > 1 else None,
        "also_consider": scored[2] if len(scored) > 2 else None,
        "source": "WalletGrower.com",
        "disclaimer": "Earning estimates are based on user reports and may vary. Not guaranteed income. Earnings depend on effort and market conditions.",
    }, indent=2)


# ---------------------------------------------------------------------------
# Verticals & Discovery
# ---------------------------------------------------------------------------

@mcp.tool()
def list_verticals() -> str:
    """
    List all product categories available from WalletGrower.

    Use this to discover what types of financial products can be searched,
    compared, and recommended. New verticals are added regularly.

    Returns:
        JSON string listing available product verticals and their endpoints
    """
    return json.dumps({
        "verticals": [
            {
                "name": "High-Yield Savings Accounts",
                "slug": "savings-accounts",
                "status": "live",
                "product_count": len(_fetch_products("savings-accounts").get("products", [])),
                "api_endpoint": f"{API_BASE}/savings-accounts",
                "tools": [
                    "search_savings_accounts",
                    "get_savings_account",
                    "compare_savings_accounts",
                    "recommend_savings_account",
                ],
            },
            {
                "name": "Credit Cards",
                "slug": "credit-cards",
                "status": "live",
                "product_count": len(_fetch_products("credit-cards").get("products", [])),
                "api_endpoint": f"{API_BASE}/credit-cards",
                "tools": [
                    "search_credit_cards",
                    "get_credit_card",
                    "compare_credit_cards",
                    "recommend_credit_card",
                ],
            },
            {
                "name": "Personal Loans",
                "slug": "personal-loans",
                "status": "live",
                "product_count": len(_fetch_products("personal-loans").get("products", [])),
                "api_endpoint": f"{API_BASE}/personal-loans",
                "tools": [
                    "search_personal_loans",
                    "get_personal_loan",
                    "compare_personal_loans",
                    "recommend_personal_loan",
                ],
            },
            {
                "name": "Budgeting & Savings Apps",
                "slug": "budgeting-apps",
                "status": "live",
                "product_count": len(_fetch_products("budgeting-apps").get("products", [])),
                "api_endpoint": f"{API_BASE}/budgeting-apps",
                "tools": [
                    "search_budgeting_apps",
                    "get_budgeting_app",
                    "compare_budgeting_apps",
                    "recommend_budgeting_app",
                ],
            },
            {
                "name": "Earning Products",
                "slug": "earning-products",
                "status": "live",
                "product_count": len(_fetch_products("earning-products").get("products", [])),
                "api_endpoint": f"{API_BASE}/earning-products",
                "tools": [
                    "search_earning_products",
                    "get_earning_product",
                    "compare_earning_products",
                    "recommend_earning_product",
                ],
            },
        ],
        "total_tools": 21,
        "total_verticals": 5,
        "source": "WalletGrower.com",
    }, indent=2)


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    mcp.run()
