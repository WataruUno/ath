import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from curl_cffi import requests as curl_requests
import yfinance_cookie_patch
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import requests
from io import StringIO
import unicodedata

def is_int(x):
    try:
        int(x)
        return True
    except:
        return False

session = None # curl_requests.Session(impersonate="chrome")
#yfinance_cookie_patch.patch_yfdata_cookie_basic()

st.set_page_config(page_title="ATH Watch", page_icon=":chart_with_upwards_trend:")
st.title('All-Time-High Watch')

indexes = {
    'S&P 500':'^GSPC',
    'Dow Jones Industrial Average': '^DJI',
    'NASDAQ Composite':'^IXIC',
    'NASDAQ 100': '^NDX',
    'Russell 2000': '^RUT',
    'PHLX Semiconductor':'^SOX',
    'NYSE FANG+TM': '^NYFANG',
    'Nikkei 225' : '^N225',
}
funds = {
    'S&P500': 'ｅＭＡＸＩＳ Ｓｌｉｍ 米国株式（Ｓ＆Ｐ５００）',
    'オルカン': 'ｅＭＡＸＩＳ Ｓｌｉｍ 全世界株式（オール・カントリー）',
    '先進国(除く日本)': 'ｅＭＡＸＩＳ Ｓｌｉｍ 先進国株式インデックス（除く日本）',
    '全世界(除く日本)': 'ｅＭＡＸＩＳ Ｓｌｉｍ 全世界株式（除く日本）',
    'TOPIX':'ｅＭＡＸＩＳ Ｓｌｉｍ 国内株式（ＴＯＰＩＸ）',
    'バランス(８資産均等)': 'ｅＭＡＸＩＳ Ｓｌｉｍ バランス（８資産均等型）',
    '新興国': 'ｅＭＡＸＩＳ Ｓｌｉｍ 新興国株式インデックス',
    '日経平均': 'ｅＭＡＸＩＳ Ｓｌｉｍ 国内株式（日経平均）',
    '先進国債券(除く日本)': 'ｅＭＡＸＩＳ Ｓｌｉｍ 先進国債券インデックス（除く日本）',
    'NAXDAQ100': 'ｅＭＡＸＩＳ ＮＡＳＤＡＱ１００インデックス',
    'NYダウ': 'ｅＭＡＸＩＳ ＮＹダウインデックス',
    '先進国リート(除く日本)': 'ｅＭＡＸＩＳ Ｓｌｉｍ 先進国リートインデックス（除く日本）',
    '全世界株式(3地域均等)': 'ｅＭＡＸＩＳ Ｓｌｉｍ 全世界株式（３地域均等型）',
    '国内リート': 'ｅＭＡＸＩＳ Ｓｌｉｍ 国内リートインデックス',
    '国内債券': 'ｅＭＡＸＩＳ Ｓｌｉｍ 国内債券インデックス'
}
others = {
    'Bitcoin(USD)': 'BTC-USD',
    'Ethereum(USD)': 'ETH-USD',
}

@st.cache_data(ttl=2*60*60)
def acquire_fund_data():
    req = requests.get('https://emaxis.am.mufg.jp/fund_file/setteirai/emaxis.csv')
    req.encoding = 'cp932'
    datas = pd.read_csv(StringIO(req.text), header=[0, 1]).rename(columns=lambda x: None if x.startswith('Unnamed') else x)
    datas.columns.names = ['name', 'item']
    datas = datas.T.reset_index()
    datas['name'] = datas['name'].ffill()
    datas = datas.set_index(['name', 'item']).T
    datas['Date'] = pd.to_datetime(datas['ｅＭＡＸＩＳ ＴＯＰＩＸインデックス']['基準日'])
    datas = datas.set_index('Date').xs('基準価額', axis=1, level=1)
    return datas

datas = acquire_fund_data()

col_type, col_ticker, col_category = st.columns((1, 1, 1))
with col_type:
    type = st.selectbox("Type", ['Index', 'Fund', 'Other', 'Individual Stock'])
with col_ticker:
    categories = ['Intraday', 'Closing']
    if type == 'Index':
        index = st.selectbox("Index", indexes.keys())
        ticker = indexes[index]
    elif type == 'Fund':
        fund = st.selectbox("Fund", funds.keys())
        ticker = funds[fund]
        categories = ['Closing']
    elif type == 'Other':
        asset = st.selectbox("Asset", others.keys())
        ticker = others[asset]
        categories = ['Intraday']
    elif type == 'Individual Stock':
        ticker = st.text_input("Ticker", None, max_chars=4, placeholder='AAPL')
        if ticker:
            ticker = ticker.upper()
            if is_int(ticker):
                ticker = f"{ticker}.T"
with col_category:
    category = st.selectbox("Category", categories)
    intraday = (category == 'Intraday')

if ticker is None:
    st.stop()

if type == 'Fund':
    info = {
        'longName': ticker,
        'currency': 'JPY',
        'exchangeTimezoneName':'Asia/Tokyo',
        'exchangeTimezoneShortName': 'JST',
        'marketState': 'CLOSED'
        }
    info['regularMarketTime'] = int(datas[ticker].dropna().index[-1].timestamp())
    info['regularMarketPrice'] = datas[ticker].dropna().iloc[-1]
else:
    info = yf.Ticker(ticker, session=session).info
if info.get('currency') is None:
    st.error(f"No ticker : [ {ticker} ]")
    st.stop()

unit = '$'
if info['currency'] == 'JPY':
    unit = '¥'

if type == 'Fund':
    data = datas[ticker].dropna().to_frame('Open')
    data['Adj Close'] = data['Close'] = data['High'] = data['Low'] = data['Open']
    data = data[['Adj Close', 'Close', 'High', 'Low', 'Open']].map(float)
else:
    data = yf.download(ticker, start='2000-01-01', auto_adjust=False, session=session).xs(ticker, axis=1, level=1)
price = data['Adj Close'].to_frame('price').dropna()
price['max'] = price['price'].expanding().max()
price['ath'] = (price['price'] == price['max'])
price = price.iloc[1:]
start = price[price['ath']].index[0]
price = price.loc[start:].copy()
price['term'] = price['ath'].cumsum()

st.write(f"# {unicodedata.normalize('NFKC', info['longName'])}")
st.write('## Status')
with st.container(border=True):
    st.write('### Current Price')
    nowtime = datetime.fromtimestamp(info['regularMarketTime'])
    nowtime = nowtime.astimezone(timezone.utc).astimezone(ZoneInfo(key=info['exchangeTimezoneName']))
    now_price = info['regularMarketPrice']
    st.write(f'{nowtime:%Y-%m-%d %H:%M}({info['exchangeTimezoneShortName']}) : **{unit}{now_price:,.2f}**')

    st.write('### All-Time-High')
    name = 'Close'
    if intraday:
        name = 'High'
    ath = data[name].sort_values().iloc[[-1]]
    if not intraday and info['marketState'] == 'REGULAR':
        ath = data[name].iloc[:-1].sort_values().iloc[[-1]]
    ath_time, ath_price = ath.index[-1], ath.iloc[-1]
    message = f'{ath_time:%Y-%m-%d}({info['exchangeTimezoneShortName']}) : **{unit}{ath_price:,.2f}**'
    if intraday:
        try:
            ath_day = yf.download(
                ticker, start=f'{ath_time:%Y-%m-%d}', end=f'{ath_time+pd.Timedelta(days=1):%Y-%m-%d}',
                interval='1m', auto_adjust=False, session=session).xs(ticker, axis=1, level=1)
            ath_day = ath_day.tz_convert(info['exchangeTimezoneName'])
            ath_time = ath_day['High'].sort_values().index[-1]
            message = f'{ath_time:%Y-%m-%d %H:%M}({info['exchangeTimezoneShortName']}) : **{unit}{ath_price:,.2f}**'
        except:
            message = f'{ath_time:%Y-%m-%d}({info['exchangeTimezoneShortName']}) : **{unit}{ath_price:,.2f}**'
    st.write(message)

    st.write('### Recent Low')
    name = 'Close'
    if intraday:
        name = 'Low'
    start = price[price['term'] == price['term'].max()].index[0]
    end = price[price['term'] == price['term'].max()].index[-1]
    recent_low = data.loc[start:end, name].sort_values().iloc[[0]]
    if not intraday and info['marketState'] == 'REGULAR':
        recent_low = data.iloc[:-1].loc[start:end, name].sort_values().iloc[[0]]
    recent_low_time, recent_low_price = recent_low.index[0], recent_low.iloc[0]
    message = f'{recent_low_time:%Y-%m-%d}({info['exchangeTimezoneShortName']}) : **{unit}{recent_low_price:,.2f}**'
    if intraday:
        try:
            recent_low_day = yf.download(
                ticker, start=f'{recent_low_time:%Y-%m-%d}', end=f'{recent_low_time+pd.Timedelta(days=1):%Y-%m-%d}',
                interval='1m', auto_adjust=False, session=session).xs(ticker, axis=1, level=1)
            recent_low_day = recent_low_day.tz_convert(info['exchangeTimezoneName'])
            recent_low_time = recent_low_day['Low'].sort_values().index[0]
            message = f'{recent_low_time:%Y-%m-%d %H:%M}({info['exchangeTimezoneShortName']}) : **{unit}{recent_low_price:,.2f}**'
        except:
            message = f'{recent_low_time:%Y-%m-%d}({info['exchangeTimezoneShortName']}) : **{unit}{recent_low_price:,.2f}**'
    st.write(message)

up_to_ath = (ath_price - now_price) / now_price
current_ratio = (now_price - recent_low_price) / (ath_price - recent_low_price)
message = f"- All-time-high is `{abs(up_to_ath):.2%}` {'above' if up_to_ath > 0 else 'below'} the current price."
if ath_price == now_price:
    message = f"- The current price is at All-time-high."
st.write(message)
if ath_price != recent_low_price and current_ratio < 1:
    st.write(f"- The current price is at `{current_ratio:.2%}` between recent low and all-time-high.")

st.write('## Price Movement since ATH(Closing)')
cols = st.columns((1, 1))
with cols[0]:
    from_year = st.selectbox(
        "Since",
        list(range(2000, 2025)),
        index=10,
    )
with cols[1]:
    min_days = st.selectbox(
        "drop when ATH is updated within [days]",
        [10, 30, 60, 90],
        index=1,
    )

dat = []
ath_dates = list(price[price['ath']].index)
for start, end in zip(ath_dates, ath_dates[1:] + [None]):
    d = price[start:end]
    if (d.index[-1] - d.index[0]).days < min_days and end is not None:
        continue
    if d.index[0].year < from_year and end is not None:
        continue
    dat += [go.Scatter(
        x=(d.index - d.index[0]).map(lambda x: x.days),
        y=100 * (d['price'] - d['price'].iloc[0]) / d['price'].iloc[0],
        customdata=d.apply(lambda x: f"{x.name:%Y-%m-%d}: {unit}{x['price']:.2f}", axis=1),
        name=f"{d.index[0]:%Y-%m-%d}",
        hovertemplate="%{customdata}"
    )]
fig = go.Figure(data=dat)
fig.update_traces(line={'width': 1})
fig.update_traces(selector=-1, line={'color':'black', 'width':2})
fig.update_layout(xaxis={'title': 'days from ATH'},
                 yaxis={'title': '% from ATH'})
st.plotly_chart(fig)