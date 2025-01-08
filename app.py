import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import time
import pyupbit
from ta.momentum import RSIIndicator
from ta.trend import MACD

class CryptoAnalyzer:
    def __init__(self, ticker="KRW-BTC"):
        self.ticker = ticker
        self.last_signal = 0
        
    def get_current_price(self):
        try:
            return pyupbit.get_current_price(self.ticker)
        except Exception as e:
            st.error(f"{self.ticker} 가격 조회 중 오류 발생: {e}")
            return None

    def calculate_indicators(self, interval="minute15", count=100):
        try:
            df = pyupbit.get_ohlcv(self.ticker, interval=interval, count=count)
            if df is None or df.empty:
                return None
            
            # RSI
            rsi = RSIIndicator(close=df['close'], window=14)
            df['RSI'] = rsi.rsi()
            
            # MACD
            macd = MACD(close=df['close'])
            df['MACD'] = macd.macd()
            df['MACD_Signal'] = macd.macd_signal()
            
            # 이동평균선
            df['MA5'] = df['close'].rolling(window=5).mean()
            df['MA20'] = df['close'].rolling(window=20).mean()
            
            return df
        except Exception as e:
            st.error(f"지표 계산 중 오류 발생: {e}")
            return None

    def analyze_signals(self):
        current_price = self.get_current_price()
        if current_price is None:
            return None
        
        df = self.calculate_indicators()
        if df is None or len(df) < 20:
            return None
        
        latest = df.iloc[-1]
        signals = []
        signal_strength = 0
        
        # RSI 분석
        if latest['RSI'] < 30:
            signals.append("💚 RSI 과매도 구간")
            signal_strength += 2
        elif latest['RSI'] > 70:
            signals.append("❌ RSI 과매수 구간")
            signal_strength -= 2
        
        # MACD 분석
        if latest['MACD'] > latest['MACD_Signal']:
            signals.append("💚 MACD 상승세")
            signal_strength += 1
        else:
            signals.append("❌ MACD 하락세")
            signal_strength -= 1
        
        # 이동평균선 분석
        if latest['MA5'] > latest['MA20']:
            signals.append("💚 단기 상승세")
            signal_strength += 1
        else:
            signals.append("❌ 단기 하락세")
            signal_strength -= 1

        # 매수 시그널 발생 시 표시
        if signal_strength >= 2 and self.last_signal < 2:
            st.success("💎 매수 기회!")
        
        self.last_signal = signal_strength
        
        return {
            'ticker': self.ticker,
            'current_price': current_price,
            'signals': signals,
            'signal_strength': signal_strength,
            'df': df,
            'indicators': latest
        }

def plot_price_chart(df, ticker):
    fig = go.Figure()
    
    # 캔들스틱
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='가격'
    ))
    
    # 이동평균선
    fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], name='MA5', line=dict(color='orange')))
    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name='MA20', line=dict(color='blue')))
    
    fig.update_layout(
        title=f'{ticker} 가격 차트',
        yaxis_title='가격',
        height=400,
        margin=dict(l=0, r=0, t=30, b=0)
    )
    
    return fig

def get_signal_color(strength):
    if strength >= 2:
        return "green"
    elif strength == 1:
        return "lightgreen"
    elif strength == 0:
        return "gray"
    elif strength == -1:
        return "pink"
    else:
        return "red"

def get_signal_message(strength):
    if strength >= 2:
        return "강력 매수", "적극적인 매수 기회입니다! 🚀"
    elif strength == 1:
        return "매수", "매수를 고려해볼 수 있습니다."
    elif strength == 0:
        return "중립", "관망이 필요한 구간입니다."
    elif strength == -1:
        return "매도", "매도를 고려해볼 수 있습니다."
    else:
        return "강력 매도", "적극적인 매도 기회입니다! ⚠️"

def main():
    st.set_page_config(
        page_title="실시간 암호화폐 분석",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    st.title("실시간 암호화폐 분석 대시보드 📊")
    
    # 기본 코인 설정
    tickers = ["KRW-BTC", "KRW-DOGE"]
    
    # 사이드바 설정
    st.sidebar.title("설정")
    update_interval = st.sidebar.slider("업데이트 주기 (초)", 3, 30, 5)
    
    # 메인 컨테이너
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    st.write(f"마지막 업데이트: {current_time}")
    
    cols = st.columns(len(tickers))
    analyzers = {ticker: CryptoAnalyzer(ticker) for ticker in tickers}
    
    for i, ticker in enumerate(tickers):
        analyzer = analyzers[ticker]
        result = analyzer.analyze_signals()
        
        if result is not None:
            with cols[i]:
                # 코인 이름과 가격
                coin_name = "비트코인" if ticker == "KRW-BTC" else "도지코인"
                st.subheader(f"{coin_name} ({ticker.replace('KRW-', '')})")
                
                # 가격 정보
                st.metric(
                    "현재 가격",
                    f"{result['current_price']:,}원"
                )
                
                # 시그널 표시
                signal_color = get_signal_color(result['signal_strength'])
                signal_title, signal_desc = get_signal_message(result['signal_strength'])
                
                st.markdown(
                    f'<div style="padding:10px;border-radius:10px;background-color:{signal_color};'
                    f'color:white;text-align:center;margin:10px 0;">'
                    f'<h3 style="margin:0">{signal_title}</h3>'
                    f'<p style="margin:0">{signal_desc}</p>'
                    '</div>',
                    unsafe_allow_html=True
                )
                
                # 시그널 목록
                for signal in result['signals']:
                    st.write(signal)
                
                # 차트
                st.plotly_chart(plot_price_chart(result['df'], ticker), use_container_width=True)
    
    time.sleep(update_interval)
    st.experimental_rerun()

if __name__ == "__main__":
    main()
