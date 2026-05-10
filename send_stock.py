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
MARKET = {"KOSPI": "01", "KOSDAQ": "02"}


def fetch_top(gubun: str, market_name: str, side: str, top_n: int = 10) -> list:
    sosok = MARKET[market_name]
    url = f"{IFRAME_URL}?sosok={sosok}&investor_gubun={gubun}&type={side}"
    res = requests.get(url, headers=NAVER_HEADERS, timeout=15)
    tables = pd.read_html(StringIO(res.text), encoding="utf-8")
    df = next((t for t in tables if "종목명" in t.columns and len(t) > 3), None)
    if df is None:
        return []
    df = df.dropna(subset=["종목명"])
    df = df[df["종목명"].str.strip() != ""]
    return [(row["종목명"], market_name, row["수량"], row["금액"] / 100)
            for _, row in df.head(top_n).iterrows()]


def build_message(date_str: str) -> str:
    lines = [f"고래 매매 현황 ({date_str})", ""]

    for investor_name, gubun in (("기관", "1000"), ("외국인", "9000")):
        lines.append(f"[{investor_name}]")
        for side, label in (("buy", "▲ 순매수 TOP 3"), ("sell", "▼ 순매도 TOP 3")):
            rows_all = []
            for market in ("KOSPI", "KOSDAQ"):
                rows_all.extend(fetch_top(gubun, market, side, top_n=10))
            rows_all.sort(key=lambda x: x[3], reverse=True)
            lines.append(label)
            for i, (name, mkt, qty, bil) in enumerate(rows_all[:3], 1):
                lines.append(f"  {i}. [{mkt}] {name}  {qty:.0f}천주 ({bil:.0f}억)")
        lines.append("")

    return "\n".join(lines)


def send_telegram(chat_id: str, text: str):
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
    date_str = get_today_str()
    print(f"기준일: {date_str}")
    message = build_message(date_str)
    print(message)
    send_telegram(CHAT_ID, message)


if __name__ == "__main__":
    main()
