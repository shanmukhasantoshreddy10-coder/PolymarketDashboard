import streamlit as st
import pandas as pd
import requests
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
from zoneinfo import ZoneInfo
import ast

# --------------------
# CONFIG
# --------------------
st.set_page_config(page_title="Polymarket Dashboard", layout="wide")
st.title("📊 Polymarket Dashboard - Live Markets")

# --------------------
# AUTO-REFRESH EVERY 10 SECONDS
# --------------------
st_autorefresh(interval=10000, limit=None, key="polymarket_autorefresh")

# --------------------
# SESSION STATE
# --------------------
for key, default in [("trade_amount", 50), ("min_profit_alert", 0.01), ("alerted_markets", set())]:
    if key not in st.session_state:
        st.session_state[key] = default

# --------------------
# INPUTS
# --------------------
trade_amount = st.number_input("Enter trade amount ($)", min_value=1, key="trade_amount")
min_profit_alert = st.number_input("Minimum profit for Telegram alerts", min_value=0.0, max_value=1.0, step=0.01, key="min_profit_alert")

# --------------------
# TELEGRAM CONFIG
# --------------------
try:
    telegram_token = st.secrets["telegram"]["bot_token"]
    telegram_chat_id = st.secrets["telegram"]["chat_id"]
    telegram_enabled = True
except:
    telegram_enabled = False

def send_telegram(message):
    if telegram_enabled:
        url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
        try:
            resp = requests.post(url, data={"chat_id": telegram_chat_id, "text": message})
            if resp.status_code != 200:
                st.warning(f"Telegram error: {resp.text}")
        except Exception as e:
            st.warning(f"Telegram failed: {e}")

def et_now():
    return datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d %H:%M:%S")

def highlight_profit(val):
    return 'background-color: lightgreen' if val > 0 else ''

# --------------------
# FETCH MARKETS
# --------------------
try:
    url = "https://gamma-api.polymarket.com/markets"
    response = requests.get(url)
    markets = response.json()
except Exception as e:
    markets = []
    st.warning(f"⚠️ Could not fetch markets: {e}")

# --------------------
# PROCESS MARKETS & TELEGRAM ALERTS
# --------------------
data = []

for market in markets:
    try:
        status = market.get("status", "open")
        question = market.get("question") or "No question"
        prices = market.get("outcomePrices")
        created_at = market.get("createdAt")
        slug = market.get("slug") or ""
        market_key = slug

        # Only open markets and recent ones
        if status != "open":
            continue
        if created_at:
            market_time = datetime.fromisoformat(created_at.replace("Z","+00:00"))
            if market_time.year < 2023:
                continue
        # Skip invalid prices
        if not prices or "oops" in question.lower():
            continue
        if isinstance(prices, str):
            try:
                prices = ast.literal_eval(prices)
            except:
                continue
        try:
            prices = [float(p) for p in prices]
        except:
            continue

        # Calculate profit
        profit = round(max(0, 1 - sum(prices)), 3)

        data.append({
            "Market": question,
            "Prices": prices,
            "Profit": profit,
            "Trade Amount": trade_amount,
            "Trade Link": f"https://polymarket.com/event/{slug}",
            "Status": status
        })

        # Telegram alert (once per market)
        if profit >= min_profit_alert and market_key not in st.session_state.alerted_markets:
            send_telegram(f"📢 Profitable trade!\nMarket: {question}\nProfit: {profit}\nTime: {et_now()} ET\nLink: https://polymarket.com/event/{slug}")
            st.session_state.alerted_markets.add(market_key)

    except:
        continue

# --------------------
# DISPLAY TABLE
# --------------------
st.subheader("Valid live markets")
df = pd.DataFrame(data)
if df.empty:
    st.info("No valid open markets found.")
else:
    st.dataframe(df.style.applymap(highlight_profit, subset=['Profit']))

# --------------------
# TEST TELEGRAM BUTTON
# --------------------
if telegram_enabled:
    if st.button("Send Test Telegram Alert"):
        send_telegram(f"✅ This is a test alert from your Polymarket dashboard! Time: {et_now()} ET")
        st.success("Test message sent! Check your Telegram.")