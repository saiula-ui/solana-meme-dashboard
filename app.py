import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import time

st.set_page_config(page_title="Solana Meme Dashboard", layout="wide")

DEX_API = "https://api.dexscreener.com/latest/dex/search/?q=solana"
SOLSCAN_META = "https://public-api.solscan.io/token/meta"

@st.cache_data(ttl=60)
def fetch_tokens():
    try:
        r = requests.get(DEX_API, timeout=15)
        data = r.json().get('pairs', [])[:150]
        rows = []
        for p in data:
            base = p.get('baseToken', {})
            rows.append({
                'Token': base.get('symbol', ''),
                'Name': base.get('name', ''),
                'Pair Address': p.get('pairAddress'),
                'Base Token Address': base.get('address'),
                'Pair Age (hrs)': round((datetime.utcnow().timestamp()*1000 - p.get('pairCreatedAt', 0))/1000/3600, 1) if p.get('pairCreatedAt') else None,
                'Price USD': p.get('priceUsd'),
                'Volume 24h': p.get('volume', {}).get('h24'),
                'Liquidity USD': p.get('liquidity', {}).get('usd'),
                'DEX': p.get('dexId'),
                'Price Change 24h': p.get('priceChange', {}).get('h24')
            })
        return pd.DataFrame(rows)
    except Exception as e:
        st.error(f"DexScreener API error: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def get_solscan_meta(token_address):
    if not token_address:
        return {}
    try:
        r = requests.get(f"{SOLSCAN_META}?tokenAddress={token_address}", timeout=8)
        if r.status_code == 200:
            data = r.json()
            return {
                'icon': data.get('icon'),
                'website': data.get('website'),
                'twitter': data.get('twitter'),
                'telegram': data.get('telegram'),
                'description': data.get('description')
            }
    except:
        pass
    return {}

st.title('🚀 Solana Meme Coin Narrative Dashboard')
st.caption('DexScreener + Solscan Token Details | Trending + Revival Hunting')

# Sidebar filters
age_filter = st.sidebar.slider('Minimum pair age (hours)', 0, 168, 0)
min_liq = st.sidebar.number_input('Minimum liquidity (USD)', 0, 1000000, 10000, step=1000)
search = st.sidebar.text_input('Search token symbol')

df = fetch_tokens()

if not df.empty:
    # Add Solscan metadata
    meta_cache = {}
    for idx, row in df.iterrows():
        addr = row['Base Token Address']
        if addr and addr not in meta_cache:
            meta_cache[addr] = get_solscan_meta(addr)
    
    # Merge metadata
    for col in ['icon', 'website', 'twitter', 'telegram', 'description']:
        df[col] = df['Base Token Address'].map(lambda a: meta_cache.get(a, {}).get(col))
    
    filtered = df[(df['Pair Age (hrs)'] >= age_filter) & (df['Liquidity USD'] >= min_liq)]
    if search:
        filtered = filtered[filtered['Token'].str.contains(search.upper(), na=False)]
    
    # Make Token clickable
    filtered = filtered.copy()
    filtered['Token'] = filtered.apply(
        lambda x: f"[{x['Token']}](https://solscan.io/token/{x['Base Token Address']})" 
        if x['Base Token Address'] else x['Token'], axis=1
    )
    
    st.subheader('📊 Trending / Filtered Tokens')
    st.dataframe(
        filtered[[
            'Token', 'Name', 'Pair Age (hrs)', 'Price USD', 'Volume 24h',
            'Liquidity USD', 'Price Change 24h', 'DEX'
        ]],
        use_container_width=True,
        column_config={
            "icon": st.column_config.ImageColumn("Icon", width="small"),
            "Token": st.column_config.TextColumn("Token", help="Click to view on Solscan")
        }
    )
    
    st.subheader('🔄 Older Pair Revival Candidates (>72h)')
    revivals = filtered[filtered['Pair Age (hrs)'] > 72].sort_values('Volume 24h', ascending=False)
    st.dataframe(revivals, use_container_width=True)
    
    # Socials summary
    with st.expander("📢 Tokens with Social Links"):
        socials = filtered.dropna(subset=['twitter', 'website']).copy()
        st.dataframe(socials[['Token', 'twitter', 'website', 'telegram']], use_container_width=True)

else:
    st.info('No data loaded. Please refresh.')

st.caption("Data from DexScreener + Public Solscan API")
