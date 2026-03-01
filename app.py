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
log_container = st.container()

try:
    url = "https://gamma-api.polymarket.com/markets"
    response = requests.get(url)
    markets = response.json()
    with log_container:
        st.markdown(f"**[{et_now()} ET] Markets fetched: {len(markets)}**")
except Exception as e:
    markets = []
    st.warning(f"⚠️ Could not fetch markets: {e}")

# --------------------
# DEBUG PANEL: all market timestamps
# --------------------
st.subheader("All fetched markets (timestamps and status)")
for m in markets:
    st.text(f"{m.get('question')} | Created: {m.get('createdAt')} | Status: {m.get('status')}")

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

        # Skip really old markets (<2023)
        if created_at:
            market_time = datetime.fromisoformat(created_at.replace("Z","+00:00"))
            if market_time.year < 2023:
                st.text(f"Skipped (too old market): {question}")
                continue

        # Skip non-open markets
        if status != "open":
            st.text(f"Skipped (not open): {question}")
            continue

        # Parse prices safely
        if isinstance(prices, str):
            try:
                prices = ast.literal_eval(prices)
            except:
                st.text(f"Skipped (cannot parse prices): {question}")
                continue
        try:
            prices = [float(p) for p in prices]
        except:
            st.text(f"Skipped (non-numeric prices): {question}")
            continue

        # Skip markets with "oops" in question
        if "oops" in question.lower():
            st.text(f"Skipped (invalid market): {question}")
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
            st.success(f"Alert sent for: {question}")
        else:
            st.text(f"No alert for {question}. Profit: {profit}, Threshold: {min_profit_alert}, Already alerted: {market_key in st.session_state.alerted_markets}")

    except Exception as e:
        st.text(f"Error processing market {question}: {e}")
        continue

# --------------------
# DISPLAY TABLE
# --------------------
st.subheader("Valid live markets")
if data:
    df = pd.DataFrame(data)
    st.dataframe(df.style.applymap(highlight_profit, subset=['Profit']))
else:
    st.info("No valid open markets found.")

# --------------------
# TEST TELEGRAM BUTTON
# --------------------
if telegram_enabled:
    if st.button("Send Test Telegram Alert"):
        send_telegram(f"✅ This is a test alert from your Polymarket dashboard! Time: {et_now()} ET")
        st.success("Test message sent! Check your Telegram.")