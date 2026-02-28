import streamlit as st
import pandas as pd
import requests
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
from zoneinfo import ZoneInfo  # for ET timezone

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
# INPUTS
# --------------------
trade_amount = st.number_input("Enter trade amount ($)", min_value=1, value=50)
min_profit_alert = st.slider("Minimum Profit for Telegram Alerts", 0.0, 0.5, 0.01, 0.01)

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
log_container = st.container()  # Streamlit container for real-time log

try:
    url = "https://gamma-api.polymarket.com/markets"
    response = requests.get(url)
    markets = response.json()
    last_fetch = et_now()

    # Log update info
    with log_container:
        st.markdown(f"**[{last_fetch} ET] Markets fetched:** {len(markets)}")

except:
    markets = []
    with log_container:
        st.warning("⚠️ Could not fetch markets from Polymarket API.")

# Fallback sample markets
if not markets:
    markets = [
        {"question": "Bitcoin > $40k by March", "outcomePrices": [0.42,0.32,0.19], "slug":"btc-march"},
        {"question": "Candidate A wins election", "outcomePrices": [0.45,0.30,0.20], "slug":"election"},
        {"question": "Ethereum > $2k by April", "outcomePrices": [0.48,0.33,0.18], "slug":"eth-april"},
    ]
    with log_container:
        st.info("Showing sample markets because live API returned nothing.")

# --------------------
# PROCESS DATA & TELEGRAM ALERTS
# --------------------
data = []
for market in markets:
    try:
        prices = [float(p) for p in market.get("outcomePrices", [])]
        total = sum(prices)
        profit = round(max(0, 1 - total), 3)

        data.append({
            "Market": market.get("question", "Unknown"),
            "Prices": prices,
            "Profit": profit,
            "Trade Amount": trade_amount,
            "Trade Link": f"https://polymarket.com/event/{market.get('slug','')}"
        })

        # Telegram alert if profit above threshold
        if profit >= min_profit_alert:
            msg = f"📢 Profitable trade!\nMarket: {market.get('question','Unknown')}\nProfit: {profit}\nTime: {et_now()} ET\nTrade Link: https://polymarket.com/event/{market.get('slug','')}"
            send_telegram(msg)

        # Log each market
        with log_container:
            st.text(f"[{et_now()} ET] Market: {market.get('question','Unknown')} | Profit: {profit}")

    except:
        continue

# Ensure DataFrame has correct columns
columns = ["Market","Prices","Profit","Trade Amount","Trade Link"]
df = pd.DataFrame(data, columns=columns)
st.dataframe(df.style.applymap(highlight_profit, subset=['Profit']))

# --------------------
# TELEGRAM TEST BUTTON
# --------------------
if telegram_enabled:
    if st.button("Send Test Telegram Alert"):
        send_telegram(f"✅ This is a test alert from your Polymarket dashboard! Time: {et_now()} ET")
        st.success("Test message sent! Check your Telegram.")