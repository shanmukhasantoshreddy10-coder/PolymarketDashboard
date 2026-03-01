import streamlit as st
import pandas as pd
import requests
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
from zoneinfo import ZoneInfo
import ast  # for parsing string lists

# --------------------
# CONFIG
# --------------------
st.set_page_config(page_title="Polymarket Dashboard", layout="wide")
st.title("📊 Polymarket Arbitrage Dashboard")

# --------------------
# AUTO-REFRESH
# --------------------
st_autorefresh(interval=10000, limit=None, key="polymarket_autorefresh")

# --------------------
# SESSION STATE FOR PERSISTENCE
# --------------------
for key, default in [("trade_amount", 50), ("min_profit_alert", 0.01), ("alerted_markets", set())]:
    if key not in st.session_state:
        st.session_state[key] = default

# --------------------
# INPUTS WITH SESSION_STATE (number inputs)
# --------------------
trade_amount = st.number_input(
    "Enter trade amount ($)",
    min_value=1,
    key="trade_amount"
)

min_profit_alert = st.number_input(
    "Minimum profit for Telegram alerts",
    min_value=0.0,
    max_value=1.0,
    step=0.01,
    key="min_profit_alert"
)

# --------------------
# TELEGRAM SECRETS
# --------------------
try:
    telegram_token = st.secrets["telegram"]["bot_token"]
    telegram_chat_id = st.secrets["telegram"]["chat_id"]
    telegram_enabled = True
except:
    telegram_enabled = False

# --------------------
# HELPER FUNCTIONS
# --------------------
def highlight_profit(val):
    color = 'lightgreen' if val > 0 else ''
    return f'background-color: {color}'

def send_telegram(message):
    if telegram_enabled:
        url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
        try:
            requests.post(url, data={"chat_id": telegram_chat_id, "text": message})
        except:
            pass

def et_now():
    """Return current time in Eastern Time (ET)"""
    return datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d %H:%M:%S")

# --------------------
# FETCH POLYMARKET DATA & LOG
# --------------------
log_container = st.container()

try:
    url = "https://gamma-api.polymarket.com/markets"
    response = requests.get(url)
    markets = response.json()
    last_fetch = et_now()
    with log_container:
        st.markdown(f"**[{last_fetch} ET] Markets fetched:** {len(markets)}")
except Exception as e:
    markets = []
    with log_container:
        st.warning(f"⚠️ Could not fetch markets from Polymarket API. Error: {e}")

# fallback sample markets if API fails
if not markets:
    markets = [
        {"question": "Bitcoin > $40k by March", "outcomePrices": [0.42,0.32,0.19], "slug":"btc-march", "status":"open", "createdAt":"2026-01-01T12:00:00Z"},
        {"question": "Candidate A wins election", "outcomePrices": [0.45,0.30,0.20], "slug":"election", "status":"open", "createdAt":"2026-01-01T12:00:00Z"},
        {"question": "Ethereum > $2k by April", "outcomePrices": [0.48,0.33,0.18], "slug":"eth-april", "status":"open", "createdAt":"2026-01-01T12:00:00Z"},
    ]
    with log_container:
        st.info("Showing sample markets because live API returned nothing.")

# --------------------
# PROCESS DATA & TELEGRAM ALERTS
# --------------------
data = []
for market in markets:
    try:
        # Only open markets
        status = market.get("status", "open")
        if status != "open":
            continue

        # Skip invalid markets
        prices = market.get("outcomePrices")
        question = market.get("question") or ""
        if not prices or "oops" in question.lower():
            continue

        # Skip old markets
        created_at = market.get("createdAt")
        if created_at:
            market_time = datetime.fromisoformat(created_at.replace("Z","+00:00"))
            if market_time.year < 2025:
                continue

        # parse string list if needed
        if isinstance(prices, str):
            try:
                prices = ast.literal_eval(prices)
            except:
                continue

        # convert to float
        try:
            prices = [float(p) for p in prices]
        except:
            continue

        total = sum(prices)
        profit = round(max(0, 1 - total), 3)
        slug = market.get("slug") or ""
        market_key = slug

        data.append({
            "Market": question,
            "Prices": prices,
            "Profit": profit,
            "Trade Amount": trade_amount,
            "Trade Link": f"https://polymarket.com/event/{slug}",
            "Status": status
        })

        # Telegram alert only once per market
        if profit >= min_profit_alert and market_key not in st.session_state.alerted_markets:
            msg = f"📢 Profitable trade!\nMarket: {question}\nProfit: {profit}\nTime: {et_now()} ET\nTrade Link: https://polymarket.com/event/{slug}"
            send_telegram(msg)
            st.session_state.alerted_markets.add(market_key)

        # Log each market
        with log_container:
            st.text(f"[{et_now()} ET] Market: {question} | Profit: {profit} | Status: {status}")

    except Exception as e:
        with log_container:
            st.text(f"Error processing market: {e}")
        continue

# --------------------
# DISPLAY DASHBOARD TABLE
# --------------------
columns = ["Market","Prices","Profit","Trade Amount","Trade Link","Status"]
df = pd.DataFrame(data, columns=columns)
st.dataframe(df.style.applymap(highlight_profit, subset=['Profit']))

# --------------------
# TELEGRAM TEST BUTTON
# --------------------
if telegram_enabled:
    if st.button("Send Test Telegram Alert"):
        send_telegram(f"✅ This is a test alert from your Polymarket dashboard! Time: {et_now()} ET")
        st.success("Test message sent! Check your Telegram.")