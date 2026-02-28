import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="Polymarket Dashboard", layout="wide")
st.title("📊 Polymarket Arbitrage Dashboard")

trade_amount = st.number_input("Enter trade amount ($)", min_value=1, value=50)

# Try to fetch real Polymarket data
try:
    url = "https://gamma-api.polymarket.com/markets"
    response = requests.get(url)
    markets = response.json()
except:
    markets = []

data = []

# Use sample data if API fails or returns nothing
if not markets:
    sample_markets = [
        {"question": "Bitcoin price above $40k by March", "outcomePrices": [0.42,0.32,0.19], "slug":"btc-march"},
        {"question": "Election winner candidate A", "outcomePrices": [0.45,0.30,0.20], "slug":"election"},
        {"question": "Ethereum above $2k by April", "outcomePrices": [0.48,0.33,0.18], "slug":"eth-april"},
    ]
    markets = sample_markets

for market in markets:
    try:
        prices = [float(p) for p in market["outcomePrices"]]
        total = sum(prices)
        profit = round(max(0, 1 - total), 3)  # ensure non-negative

        data.append({
            "Market": market["question"],
            "Prices": prices,
            "Profit": profit,
            "Trade Amount": trade_amount,
            "Trade Link": f"https://polymarket.com/event/{market['slug']}"
        })
    except:
        pass

df = pd.DataFrame(data)

# Highlight profitable trades
def highlight_profit(val):
    color = 'lightgreen' if val > 0 else ''
    return f'background-color: {color}'

st.dataframe(df.style.applymap(highlight_profit, subset=['Profit']))