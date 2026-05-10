import sys
import io
import os
import requests
import pandas as pd
from io import StringIO
from datetime import datetime, timedelta

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

NAVER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://finance.naver.com/sise/sise_deal_rank.naver",
}
IFRAME_URL = "https://finance.naver.com/sise/sise_deal_rank_iframe.naver"

INVESTOR = {
    "기관": "1000",
    "외국인": "9000",
}
MARKET = {
    "KOSPI": "01",
    "KOSDAQ": "02",
}




def fetch_top_buyers(investor_name: str, market_name: str, top_n: int = 10) -> pd.DataFrame:
    gubun = INVESTOR[investor_name]
    sosok = MARKET[market_name]
    url = f"{IFRAME_URL}?sosok={sosok}&investor_gubun={gubun}&type=buy"
    res = requests.get(url, headers=NAVER_HEADERS, timeout=15)
    tables = pd.read_html(StringIO(res.text), encoding="utf-8")

    df = None
    for t in tables:
        if "종목명" in t.columns and len(t) > 3:
            df = t
            break
    if df is None:
        return pd.DataFrame()

    df = df.dropna(subset=["종목명"])
    df = df[df["종목명"].str.strip() != ""]
    df["market"] = market_name
    return df.head(top_n)


def build_message(date_str: str) -> str:
    lines = [f"고래 매수 현황 ({date_str})", ""]

    for investor in ("기관", "외국인"):
        emoji = "기관" if investor == "기관" else "외국인"
        lines.append(f"[{emoji} 순매수 TOP 10]")

        rows_all = []
        for market in ("KOSPI", "KOSDAQ"):
            df = fetch_top_buyers(investor, market)
            if not df.empty:
                for _, row in df.iterrows():
                    amount_bil = row["금액"] / 100  # 백만원 -> 억원
                    rows_all.append((row["종목명"], market, row["수량"], amount_bil))

        # 금액 기준 정렬 후 TOP 10
        rows_all.sort(key=lambda x: x[3], reverse=True)
        for i, (name, mkt, qty, bil) in enumerate(rows_all[:10], 1):
            lines.append(f"  {i}. [{mkt}] {name}  {qty:.0f}천주 ({bil:.0f}억)")

        lines.append("")

    return "\n".join(lines)


def send_telegram(chat_id, text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    res = requests.post(url, json={"chat_id": chat_id, "text": text})
    if res.ok:
        print("텔레그램 전송 완료")
    else:
        print(f"전송 실패: {res.text}")


def get_today_str() -> str:
    today = datetime.today()
    if today.weekday() == 5:
        today -= timedelta(days=1)
    elif today.weekday() == 6:
        today -= timedelta(days=2)
    return today.strftime("%Y-%m-%d")


def main():
    chat_id = CHAT_ID
    date_str = get_today_str()
    print(f"기준일: {date_str}")
    print("데이터 수집 중...")

    message = build_message(date_str)
    print("\n--- 미리보기 ---")
    print(message)
    print("----------------\n")

    send_telegram(chat_id, message)


if __name__ == "__main__":
    main()
