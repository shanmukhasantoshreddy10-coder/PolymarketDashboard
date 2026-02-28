import streamlit as st
import pandas as pd
import requests
import time

# --------------------
# CONFIG
# --------------------
st.set_page_config(page_title="Polymarket Dashboard", layout="wide")
st.title("📊 Polymarket Arbitrage Dashboard")

# --------------------
# INPUTS
# --------------------
trade_amount = st.number_input("Enter trade amount ($)", min_value=1, value=50)
telegram_alerts = st.checkbox("Enable Telegram Alerts")

# If Telegram alerts are enabled, set token and chat ID
if telegram_alerts:
    telegram_token = st.text_input("Telegram Bot Token", type="password")
    telegram_chat_id = st.text_input("Telegram Chat ID")

# --------------------
# HELPER FUNCTIONS
# --------------------
def highlight_profit(val):
    color = 'lightgreen' if val > 0 else ''
    return f'background-color: {color}'

def send_telegram(message):
    if telegram_alerts and telegram_token and telegram_chat_id:
        url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
        try:
            requests.post(url, data={"chat_id": telegram_chat_id, "text": message})
        except:
            pass

# --------------------
# MAIN LOOP
# --------------------
# Using Streamlit auto-refresh: rerun every 10 seconds
st_autorefresh = st.experimental_rerun
st.experimental_set_query_params(refresh=int(time.time()))

# Try fetching Polymarket data
try:
    url = "https://gamma-api.polymarket.com/markets"
    response = requests.get(url)
    markets = response.json()
except:
    markets = []

data = []

# Sample markets if API fails
if not markets:
    markets = [
        {"question": "Bitcoin > $40k by March", "outcomePrices": [0.42,0.32,0.19], "slug":"btc-march"},
        {"question": "Candidate A wins election", "outcomePrices": [0.45,0.30,0.20], "slug":"election"},
        {"question": "Ethereum > $2k by April", "outcomePrices": [0.48,0.33,0.18], "slug":"eth-april"},
    ]

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

        # Send Telegram alert if profit > 0
        if profit > 0:
            msg = f"Profitable trade!\nMarket: {market.get('question','Unknown')}\nProfit: {profit}\nTrade Link: https://polymarket.com/event/{market.get('slug','')}"
            send_telegram(msg)
    except:
        continue

# Ensure DataFrame has correct columns even if empty
columns = ["Market","Prices","Profit","Trade Amount","Trade Link"]
df = pd.DataFrame(data, columns=columns)

# Display
if "Profit" in df.columns:
    st.dataframe(df.style.applymap(highlight_profit, subset=['Profit']))
else:
    st.dataframe(df)

# Auto-refresh every 10 seconds
st.experimental_rerun()