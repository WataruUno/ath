import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go

st.set_page_config(page_title="ATH Watch", page_icon=":chart_with_upwards_trend:")
st.title('All-Time-High Watch')

tickers = {
    'S&P 500':'^GSPC',
    'Dow Jones Industrial Average': '^DJI',
    'NASDAQ Composite':'^IXIC',
    'NASDAQ 100': '^NDX',
    'Russell 2000': '^RUT',
    'PHLX Semiconductor':'^SOX',
    'NYSE FANG+TM Index': '^NYFANG',
}
index= st.selectbox("Index", tickers.keys())
ticker = tickers[index]

data = yf.download(ticker, start='2000-01-01', auto_adjust=False).xs(ticker, axis=1, level=1)

unit = '$'

price = data['Adj Close'].to_frame('price').dropna()
price['max'] = price['price'].expanding().max()
price['ath'] = price['price'] == price['max']
price = price.iloc[1:]
start = price[price['ath']].index[0]
price = price.loc[start:].copy()
price['term'] = price['ath'].cumsum()

st.write('# Status')
with st.container(border=True):
    st.write('## Current Price')
    nowtime, now_price = price.index[-1], price['price'].iloc[-1]
    now_day = yf.download(
        ticker, start=f'{nowtime:%Y-%m-%d}', end=f'{nowtime+pd.Timedelta(days=1):%Y-%m-%d}',
        interval='1m', auto_adjust=False).xs(ticker, axis=1, level=1)
    now_day = now_day.tz_convert('America/New_York')
    nowtime, now_price = now_day.index[-1], now_day.iloc[-1]['Close']
    st.write(f'{nowtime:%Y-%m-%d %H:%M} : {unit}{now_price:,.2f}')

    st.write('## All-Time-High')
    ath = data['High'].sort_values().iloc[[-1]]
    ath_time, ath_price = ath.index[-1], ath.iloc[-1]
    try:
        ath_day = yf.download(
            ticker, start=f'{ath_time:%Y-%m-%d}', end=f'{ath_time+pd.Timedelta(days=1):%Y-%m-%d}',
            interval='1m', auto_adjust=False).xs(ticker, axis=1, level=1)
        ath_day = ath_day.tz_convert('America/New_York')
        ath_time = ath_day['High'].sort_values().index[-1]
        st.write(f'{ath_time:%Y-%m-%d} : {unit}{ath_price:,.2f}')
    except:
        st.write(f'{ath_time:%Y-%m-%d} : {unit}{ath_price:,.2f}')

    st.write('## Recent Low')
    start = price[price['term'] == price['term'].max()].index[0]
    end = price[price['term'] == price['term'].max()].index[-1]
    recent_low = data.loc[start:end, 'Low'].sort_values().iloc[[0]]
    recent_low_time, recent_low_price = recent_low.index[0], recent_low.iloc[0]
    try:
        recent_low_day = yf.download(
            ticker, start=f'{recent_low_time:%Y-%m-%d}', end=f'{recent_low_time+pd.Timedelta(days=1):%Y-%m-%d}',
            interval='1m', auto_adjust=False).xs(ticker, axis=1, level=1)
        recent_low_day = recent_low_day.tz_convert('America/New_York')
        recent_low_time = recent_low_day['Low'].sort_values().index[0]
        st.write(f'{recent_low_time:%Y-%m-%d %H:%M} : {unit}{recent_low_price:,.2f}')
    except:
        st.write(f'{recent_low_time:%Y-%m-%d} : {unit}{recent_low_price:,.2f}')

st.write(f"- All-time-high is {(ath_price - now_price) /now_price:.2%} above the current price.")
st.write(f"- Current price is at {(now_price -recent_low_price) / (ath_price - recent_low_price):.2%} between recent low and all-time-high.")

st.write('# Price Movement since ATH(close)')
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
fig.update_traces(selector=-1,line=dict(color='black',width=3))
fig.update_layout(xaxis={'title': 'days from ATH'},
                 yaxis={'title': '% from ATH'})
st.plotly_chart(fig)