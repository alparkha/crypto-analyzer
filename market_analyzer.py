import time
from datetime import datetime
import pyupbit
import pandas as pd
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD, ADXIndicator, IchimokuIndicator
from ta.volume import OnBalanceVolumeIndicator, ForceIndexIndicator
import numpy as np
import matplotlib.pyplot as plt
import mplfinance as mpf
from playsound import playsound
import os
from pathlib import Path

class CryptoAnalyzer:
    def __init__(self, ticker="KRW-BTC"):
        self.ticker = ticker
        self.price_alerts = {}  # 가격 알림 설정
        self.last_volume = None  # 이전 거래량
        self.volume_alert_threshold = 2.0  # 거래량 급증 기준 (200%)
        self.chart_dir = "charts"  # 차트 저장 디렉토리
        Path(self.chart_dir).mkdir(exist_ok=True)

    def get_current_price(self):
        """현재가 조회"""
        try:
            price = None
            for _ in range(3):  # 최대 3번 재시도
                try:
                    price = pyupbit.get_current_price(self.ticker)
                    if price is not None:
                        break
                    time.sleep(0.5)
                except Exception:
                    time.sleep(0.5)
            return price
        except Exception as e:
            print(f"{self.ticker} 가격 조회 중 오류 발생: {e}")
            return None

    def set_price_alert(self, target_price, alert_type="above"):
        """가격 알림 설정"""
        self.price_alerts[target_price] = alert_type
        print(f"{self.ticker} {target_price:,}원 {alert_type} 알림 설정 완료")

    def check_price_alerts(self, current_price):
        """가격 알림 체크"""
        alerts_to_remove = []
        for target_price, alert_type in self.price_alerts.items():
            if alert_type == "above" and current_price > target_price:
                print(f"\n {self.ticker} 가격이 {target_price:,}원을 돌파했습니다!")
                playsound("alert.mp3")
                alerts_to_remove.append(target_price)
            elif alert_type == "below" and current_price < target_price:
                print(f"\n {self.ticker} 가격이 {target_price:,}원 아래로 떨어졌습니다!")
                playsound("alert.mp3")
                alerts_to_remove.append(target_price)
        
        for price in alerts_to_remove:
            del self.price_alerts[price]

    def check_volume_surge(self, df):
        """거래량 급증 체크"""
        if df is None or len(df) < 2:
            return
        
        current_volume = df['volume'].iloc[-1]
        if self.last_volume is not None:
            volume_change = current_volume / self.last_volume
            if volume_change > self.volume_alert_threshold:
                print(f"\n {self.ticker} 거래량 급증! ({volume_change:.1f}배)")
                playsound("alert.mp3")
        
        self.last_volume = current_volume

    def plot_chart(self, df):
        """차트 그리기"""
        if df is None or len(df) < 60:
            return
        
        style = mpf.make_mpf_style(base_mpf_style='charles', gridstyle='', facecolor='white')
        
        add_plots = [
            mpf.make_addplot(df['RSI'], panel=1, color='purple', title='RSI'),
            mpf.make_addplot(df['Stoch_K'], panel=1, color='blue', secondary_y=True),
            mpf.make_addplot(df['Stoch_D'], panel=1, color='red', secondary_y=True),
            mpf.make_addplot(df['MACD'], panel=2, color='blue', title='MACD'),
            mpf.make_addplot(df['MACD_Signal'], panel=2, color='orange'),
            mpf.make_addplot(df['ADX'], panel=3, color='black', title='DMI'),
            mpf.make_addplot(df['DI_plus'], panel=3, color='green'),
            mpf.make_addplot(df['DI_minus'], panel=3, color='red'),
            mpf.make_addplot(df['MA5'], color='red'),
            mpf.make_addplot(df['MA20'], color='blue'),
            mpf.make_addplot(df['MA60'], color='green'),
            mpf.make_addplot(df['MA120'], color='purple'),
            mpf.make_addplot(df['Ichimoku_SpanA'], color='orange', alpha=0.3),
            mpf.make_addplot(df['Ichimoku_SpanB'], color='green', alpha=0.3)
        ]
        
        chart_file = f"{self.chart_dir}/{self.ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        fig, axes = mpf.plot(
            df,
            type='candle',
            addplot=add_plots,
            style=style,
            volume=True,
            returnfig=True,
            title=f'\n{self.ticker} Technical Analysis\n',
            figsize=(15, 10)
        )
        plt.savefig(chart_file)
        plt.close()
        
        print(f"차트 저장됨: {chart_file}")

    def calculate_indicators(self, interval="minute60", count=200):
        """기술적 지표 계산"""
        try:
            df = None
            for _ in range(3):  # 최대 3번 재시도
                try:
                    df = pyupbit.get_ohlcv(self.ticker, interval=interval, count=count)
                    if df is not None and not df.empty:
                        break
                    time.sleep(0.5)
                except Exception:
                    time.sleep(0.5)
            
            if df is None or df.empty:
                return None
            
            # RSI
            rsi = RSIIndicator(close=df['close'], window=14)
            df['RSI'] = rsi.rsi()
            
            # MACD
            macd = MACD(close=df['close'])
            df['MACD'] = macd.macd()
            df['MACD_Signal'] = macd.macd_signal()
            df['MACD_Hist'] = macd.macd_diff()
            
            # Stochastic
            stoch = StochasticOscillator(high=df['high'], low=df['low'], close=df['close'], window=14, smooth_window=3)
            df['Stoch_K'] = stoch.stoch()
            df['Stoch_D'] = stoch.stoch_signal()
            
            # DMI (Directional Movement Index)
            adx = ADXIndicator(high=df['high'], low=df['low'], close=df['close'], window=14)
            df['ADX'] = adx.adx()
            df['DI_plus'] = adx.adx_pos()
            df['DI_minus'] = adx.adx_neg()
            
            # OBV (On Balance Volume)
            obv = OnBalanceVolumeIndicator(close=df['close'], volume=df['volume'])
            df['OBV'] = obv.on_balance_volume()
            
            # Force Index
            fi = ForceIndexIndicator(close=df['close'], volume=df['volume'])
            df['Force_Index'] = fi.force_index()
            
            # 일목균형표
            ichimoku = IchimokuIndicator(high=df['high'], low=df['low'])
            df['Ichimoku_Conversion'] = ichimoku.ichimoku_conversion_line()
            df['Ichimoku_Base'] = ichimoku.ichimoku_base_line()
            df['Ichimoku_SpanA'] = ichimoku.ichimoku_a()
            df['Ichimoku_SpanB'] = ichimoku.ichimoku_b()
            
            # 이동평균선
            df['MA5'] = df['close'].rolling(window=5).mean()
            df['MA20'] = df['close'].rolling(window=20).mean()
            df['MA60'] = df['close'].rolling(window=60).mean()
            df['MA120'] = df['close'].rolling(window=120).mean()
            
            # 볼린저 밴드
            df['BB_Middle'] = df['close'].rolling(window=20).mean()
            std = df['close'].rolling(window=20).std()
            df['BB_Upper'] = df['BB_Middle'] + (std * 2)
            df['BB_Lower'] = df['BB_Middle'] - (std * 2)
            
            # 추가 모멘텀 지표
            # ROC (Rate of Change)
            df['ROC'] = df['close'].pct_change(periods=10) * 100
            
            # Price Channel
            df['Upper_Channel'] = df['high'].rolling(window=20).max()
            df['Lower_Channel'] = df['low'].rolling(window=20).min()
            
            return df
        except Exception as e:
            print(f"지표 계산 중 오류 발생: {e}")
            return None

    def analyze_signals(self):
        """매수/매도 시그널 분석"""
        current_price = self.get_current_price()
        if current_price is None:
            return None
        
        df = self.calculate_indicators()
        if df is None or len(df) < 60:
            return None
        
        # 거래량 급증 체크
        self.check_volume_surge(df)
        
        # 가격 알림 체크
        self.check_price_alerts(current_price)
        
        # 차트 생성 (1분마다)
        if datetime.now().second < 15:
            self.plot_chart(df)
        
        latest = df.iloc[-1]
        signals = []
        signal_strength = 0
        
        result = {
            'ticker': self.ticker,
            'current_price': current_price,
            'signals': [],
            'signal_strength': 0,
            'rsi': latest['RSI'],
            'ma5': latest['MA5'],
            'ma20': latest['MA20'],
            'ma60': latest['MA60'],
            'Stoch_K': latest['Stoch_K'],
            'Stoch_D': latest['Stoch_D'],
            'ADX': latest['ADX'],
            'DI_plus': latest['DI_plus'],
            'DI_minus': latest['DI_minus'],
            'OBV': latest['OBV']
        }
        
        if latest['RSI'] < 30:
            signals.append(" RSI 과매도 구간 (매수 시그널)")
            signal_strength += 1
        elif latest['RSI'] > 70:
            signals.append(" RSI 과매수 구간 (매도 시그널)")
            signal_strength -= 1
        
        if latest['MACD'] > latest['MACD_Signal']:
            if latest['MACD_Hist'] > df['MACD_Hist'].iloc[-2]:
                signals.append(" MACD 상승 추세 강화")
                signal_strength += 1
            else:
                signals.append(" MACD 상승 추세")
        else:
            if latest['MACD_Hist'] < df['MACD_Hist'].iloc[-2]:
                signals.append(" MACD 하락 추세 강화")
                signal_strength -= 1
            else:
                signals.append(" MACD 하락 추세")
        
        if latest['MA5'] > latest['MA20'] > latest['MA60']:
            signals.append(" 이동평균선 황금 크로스")
            signal_strength += 1
        elif latest['MA5'] < latest['MA20'] < latest['MA60']:
            signals.append(" 이동평균선 데드 크로스")
            signal_strength -= 1
        
        if current_price < latest['BB_Lower']:
            signals.append(" 볼린저 밴드 하단 돌파 (매수 시그널)")
            signal_strength += 1
        elif current_price > latest['BB_Upper']:
            signals.append(" 볼린저 밴드 상단 돌파 (매도 시그널)")
            signal_strength -= 1
        
        # Stochastic 분석
        if latest['Stoch_K'] < 20 and latest['Stoch_K'] > latest['Stoch_D']:
            signals.append(" 스토캐스틱 과매도 반등 시그널")
            signal_strength += 1
        elif latest['Stoch_K'] > 80 and latest['Stoch_K'] < latest['Stoch_D']:
            signals.append(" 스토캐스틱 과매수 하락 시그널")
            signal_strength -= 1
        
        # DMI 분석
        if latest['DI_plus'] > latest['DI_minus'] and latest['ADX'] > 25:
            signals.append(" DMI 강력 상승 트렌드")
            signal_strength += 1
        elif latest['DI_minus'] > latest['DI_plus'] and latest['ADX'] > 25:
            signals.append(" DMI 강력 하락 트렌드")
            signal_strength -= 1
        
        # OBV 분석
        obv_ma = df['OBV'].rolling(window=20).mean()
        if latest['OBV'] > obv_ma.iloc[-1]:
            signals.append(" OBV 상승 트렌드 (매수세 우위)")
            signal_strength += 1
        elif latest['OBV'] < obv_ma.iloc[-1]:
            signals.append(" OBV 하락 트렌드 (매도세 우위)")
            signal_strength -= 1
        
        # 일목균형표 분석
        if (latest['close'] > latest['Ichimoku_SpanA'] and 
            latest['close'] > latest['Ichimoku_SpanB']):
            signals.append(" 일목균형표 상승 시그널")
            signal_strength += 1
        elif (latest['close'] < latest['Ichimoku_SpanA'] and 
              latest['close'] < latest['Ichimoku_SpanB']):
            signals.append(" 일목균형표 하락 시그널")
            signal_strength -= 1
        
        # ROC 분석
        if latest['ROC'] > 5:
            signals.append(" ROC 강력 상승 모멘텀")
            signal_strength += 1
        elif latest['ROC'] < -5:
            signals.append(" ROC 강력 하락 모멘텀")
            signal_strength -= 1
        
        # Price Channel 분석
        if current_price >= latest['Upper_Channel']:
            signals.append(" 상단 채널 돌파 (상승 추세 강화)")
            signal_strength += 1
        elif current_price <= latest['Lower_Channel']:
            signals.append(" 하단 채널 돌파 (하락 추세 강화)")
            signal_strength -= 1
        
        result['signals'] = signals
        result['signal_strength'] = signal_strength
        return result

def get_top_volume_tickers():
    """거래대금 상위 코인 조회"""
    try:
        tickers = pyupbit.get_tickers(fiat="KRW")
        markets = None
        for _ in range(3):  # 최대 3번 재시도
            try:
                markets = pyupbit.get_current_price(tickers)
                if markets is not None:
                    break
                time.sleep(0.5)
            except Exception:
                time.sleep(0.5)
        
        if markets is None:
            return []
        
        volume_data = []
        for ticker in tickers:
            try:
                daily_data = None
                for _ in range(3):  # 최대 3번 재시도
                    try:
                        daily_data = pyupbit.get_ohlcv(ticker, interval="day", count=1)
                        if daily_data is not None and not daily_data.empty:
                            break
                        time.sleep(0.5)
                    except Exception:
                        time.sleep(0.5)
                
                if daily_data is not None and not daily_data.empty:
                    volume = daily_data['volume'].iloc[-1] * daily_data['close'].iloc[-1]
                    volume_data.append((ticker, volume))
            except Exception:
                continue
            time.sleep(0.1)  # API 호출 간격 조절
        
        volume_data.sort(key=lambda x: x[1], reverse=True)
        return [item[0] for item in volume_data[:3]]
    except Exception as e:
        print(f"거래대금 상위 코인 조회 중 오류 발생: {e}")
        return []

def print_analysis_result(result):
    """분석 결과 출력"""
    if result is None:
        return
    
    print(f"\n{result['ticker']} 분석 리포트")
    print("="*50)
    print(f"현재 가격: {result['current_price']:,}원")
    
    # 주요 기술적 지표 값 출력
    print("\n📊 주요 지표 현황:")
    print(f"RSI: {result['rsi']:.2f}")
    if result['rsi'] > 70:
        print("   ⚠️ 과매수 구간 - 조정 가능성 높음")
    elif result['rsi'] < 30:
        print("   💡 과매도 구간 - 반등 가능성 높음")
            
    print(f"\n이동평균선:")
    print(f"MA5: {result['ma5']:.0f}")
    print(f"MA20: {result['ma20']:.0f}")
    print(f"MA60: {result['ma60']:.0f}")
        
    if result['ma5'] > result['ma20'] > result['ma60']:
        print("   💹 단기/중기/장기 모두 상승 트렌드")
    elif result['ma5'] < result['ma20'] < result['ma60']:
        print("   📉 단기/중기/장기 모두 하락 트렌드")
        
    print("\n🔍 상세 분석:")
    for signal in result['signals']:
        print(signal)
        
    print("\n💡 트레이딩 전략 추천:")
    signal_strength = result['signal_strength']
    if signal_strength >= 3:
        print("""적극적 매수 구간 🚀
- 강력한 상승 추세 확인
- 추가 상승 여력 높음
- 분할 매수 전략 추천""")
    elif signal_strength == 2:
        print("""매수 고려 구간 ⭐
- 상승 추세 진입 단계
- 리스크 분산을 위해 분할 매수 권장
- 추가 확인 후 매수 결정""")
    elif signal_strength == 1:
        print("""관망 후 매수 고려 💭
- 상승 가능성 있으나 신중한 접근 필요
- 추가 지표 확인 필요
- 소액 분할 매수 검토""")
    elif signal_strength == 0:
        print("""중립 구간 ⚖️
- 뚜렷한 추세 없음
- 적극적 매매 지양
- 추가 모니터링 필요""")
    elif signal_strength == -1:
        print("""관망 후 매도 고려 💭
- 하락 가능성 있으나 신중한 접근 필요
- 추가 지표 확인 필요
- 일부 수익 실현 검토""")
    elif signal_strength == -2:
        print("""매도 고려 구간 ⚠️
- 하락 추세 진입 단계
- 수익 실현 권장
- 리스크 관리 필요""")
    else:
        print("""적극적 매도 구간 🔥
- 강력한 하락 추세 확인
- 추가 하락 가능성 높음
- 빠른 손절 추천""")

    # 추가 분석 코멘트
    print("\n📈 추세 분석:")
    if 'Stoch_K' in result and 'Stoch_D' in result:
        if result['Stoch_K'] < 20:
            print("- 스토캐스틱: 과매도 구간, 반등 가능성 있음")
        elif result['Stoch_K'] > 80:
            print("- 스토캐스틱: 과매수 구간, 조정 가능성 있음")
        
    if 'ADX' in result:
        if result['ADX'] > 25:
            if result['DI_plus'] > result['DI_minus']:
                print("- DMI: 강력한 상승 추세 진행 중")
            else:
                print("- DMI: 강력한 하락 추세 진행 중")
        else:
            print("- DMI: 뚜렷한 추세 없음")
        
    print("\n💰 거래량 분석:")
    if 'OBV' in result:
        if result['OBV'] > result.get('OBV_MA', 0):
            print("- OBV: 매수세 우위, 상승 추세 지속 가능성 높음")
        else:
            print("- OBV: 매도세 우위, 하락 추세 지속 가능성 높음")
        
    print("\n⚡ 단기 매매 전략:")
    if signal_strength > 0:
        print("""- 지지선: 이동평균선과 일목균형표 구름대 활용
- 손절가: 최근 저점 아래로 하락 시
- 목표가: 이전 고점 또는 상단 채널 라인""")
    elif signal_strength < 0:
        print("""- 저항선: 이동평균선과 일목균형표 구름대 활용
- 손절가: 최근 고점 위로 상승 시
- 목표가: 이전 저점 또는 하단 채널 라인""")
        
    print("\n⚠️ 리스크 관리:")
    print("- 투자금의 1-2% 이상 손실 시 손절 권장")
    print("- 분할 매매로 리스크 분산")
    print("- 추세 전환 시 즉시 대응 필요")
        
    print("\n=== 분석 완료 ===")

def main():
    base_tickers = ["KRW-BTC", "KRW-DOGE"]
    analyzers = {ticker: CryptoAnalyzer(ticker) for ticker in base_tickers}
    
    analyzers["KRW-BTC"].set_price_alert(100000000, "above")
    analyzers["KRW-BTC"].set_price_alert(90000000, "below")
    
    print("암호화폐 자동 매매 시그널 분석 시작...")
    print("15초마다 업데이트됩니다.")
    print("기본 분석 코인: Bitcoin, Dogecoin + 거래대금 상위 3개")
    print("="*70)
    
    while True:
        try:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"\n[{current_time}] 분석 시작")
            print("="*70)
            
            # 거래대금 상위 코인 분석
            top_tickers = get_top_volume_tickers()
            if not top_tickers:
                print("거래대금 상위 코인 조회 실패")
            
            # 새로운 코인 추가
            for ticker in top_tickers:
                if ticker not in analyzers:
                    analyzers[ticker] = CryptoAnalyzer(ticker)
            
            # 모든 코인 분석
            for ticker, analyzer in analyzers.items():
                try:
                    result = analyzer.analyze_signals()
                    if result is not None:
                        print_analysis_result(result)
                        print("-"*70)
                    else:
                        print(f"{ticker} 분석 실패")
                except Exception as e:
                    print(f"{ticker} 분석 중 오류 발생: {e}")
            
            time.sleep(15)
            
        except KeyboardInterrupt:
            print("\n프로그램을 종료합니다.")
            break
        except Exception as e:
            print(f"오류 발생: {e}")
            time.sleep(15)
            continue

if __name__ == "__main__":
    main()
