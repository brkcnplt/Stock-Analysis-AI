import os
import re
import warnings
import requests
from bs4 import BeautifulSoup
from tabulate import tabulate
import yfinance as yf
from datetime import datetime, timedelta
from dotenv import load_dotenv
import google.generativeai as genai

# ---------------- Uyarıları kapat ----------------
warnings.filterwarnings("ignore")

# ---------------- .env Yükle ----------------
load_dotenv()
GENAI_API_KEY = os.getenv("GENAI_API_KEY")
SCORECARD_URL = os.getenv("SCORECARD_URL")

if not GENAI_API_KEY or not SCORECARD_URL:
    raise ValueError(".env dosyasında GENAI_API_KEY veya SCORECARD_URL bulunamadı!")

# ---------------- Yardımcı Fonksiyonlar ----------------
def safe_float(val):
    try:
        if val is None:
            return None
        if isinstance(val, (int, float)):
            return float(val)
        if not val or val.strip() in ["-", "N/A", ""]:
            return None
        return float(val.replace(",", "."))
    except:
        return None

def calc_median(values):
    values = sorted(values)
    n = len(values)
    if n == 0:
        return None
    return values[n // 2] if n % 2 == 1 else (values[n // 2 - 1] + values[n // 2]) / 2

def get_price(df):
    if df.empty:
        return None
    for col in ["Adj Close", "Close"]:
        if col in df.columns:
            return float(df[col].iloc[0])
    # Eğer Close sütunu farklı adla gelirse
    for col in df.columns:
        if "Close" in col:
            return float(df[col].iloc[0])
    return None

# ---------------- Scraping Fonksiyonu ----------------
def fetch_financial_data(stock_code, donem=None):
    """Scorecard sayfasından carpanlar ve karlilik verilerini getirir"""
    headers = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/x-www-form-urlencoded"}
    data = {"SeciliHisse": stock_code}
    if donem:
        data["SeciliHisseDonem"] = donem
    try:
        response = requests.post(SCORECARD_URL, headers=headers, data=data)
        response.raise_for_status()
    except Exception as e:
        print(f"POST isteği başarısız:")
        return None, None

    soup = BeautifulSoup(response.text, "html.parser")
    carpanlar_div = soup.find("div", id="carpanlar")
    karlilik_div = soup.find("div", id="karlilik")
    return carpanlar_div, karlilik_div

# ---------------- Hisse Analizi Fonksiyonu ----------------
def analyze_stock(stock_code):
    table_data = []
    net_kar_marjlari = []

    # 1. Veri Çek
    carpanlar_div, karlilik_div = fetch_financial_data(stock_code)
    if not carpanlar_div or not karlilik_div:
        print("Çarpanlar veya Karlılık tabı bulunamadı.")
        return

    # 2. Net Kar Marjları
    for row in karlilik_div.find_all("tr"):
        period_cell = row.find("td", class_="dt-left")
        net_kar_cell = row.find("td", class_="dt-right dd7")
        if period_cell and re.match(r"\d{4}/\d{2}", period_cell.text.strip()):
            val = safe_float(net_kar_cell.text.strip()) if net_kar_cell else None
            if val is not None:
                net_kar_marjlari.append(val)

    # 3. Çarpanlar
    current_donem = None
    for idx, row in enumerate(carpanlar_div.find_all("tr")):
        period_cell = row.find("td", class_="dt-left")
        if not period_cell:
            continue
        period = period_cell.text.strip()
        if idx == 1:
            current_donem = period
            year, month = current_donem.split("/")
            new_donem = f"{int(year)-4}/{month}"

        if not re.match(r"\d{4}/\d{2}", period):
            continue

        fk = row.find("td", class_="dt-right dd2")
        pddd = row.find("td", class_="dt-right dd3")
        fd_favok = row.find("td", class_="dt-right dd4")
        fd_satis = row.find("td", class_="dt-right dd5")
        eps = row.find("td", class_="dt-right dd6")

        table_data.append([
            period,
            fk.text.strip() if fk else "N/A",
            pddd.text.strip() if pddd else "N/A",
            fd_favok.text.strip() if fd_favok else "N/A",
            fd_satis.text.strip() if fd_satis else "N/A",
            eps.text.strip() if eps else "N/A"
        ])

    # 4. MEDYAN Hesapla
    numeric_cols = list(zip(*table_data))[1:]
    medians = []
    for col in numeric_cols:
        nums = [safe_float(x) for x in col if safe_float(x) is not None]
        medians.append(round(calc_median(nums), 2) if nums else "N/A")

    net_kar_marji_median = round(calc_median(net_kar_marjlari), 2) if net_kar_marjlari else "N/A"
    med_row = [
        "MEDYAN (8 Yıllık)",
        f"{medians[0]:.2f}" if isinstance(medians[0], float) else "N/A",
        f"{medians[1]:.2f}" if isinstance(medians[1], float) else "N/A",
        f"{medians[2]:.2f}" if isinstance(medians[2], float) else "N/A",
        f"{medians[3]:.2f}" if isinstance(medians[3], float) else "N/A",
        f"{net_kar_marji_median:.2f}%" if isinstance(net_kar_marji_median, float) else "N/A"
    ]

    # 5. Yahoo Finance Verisi
    try:
        ticker = yf.Ticker(f"{stock_code}.IS")
        info = ticker.info
        yahoo_row = [
            "Güncel Çarpanlar",
            f"{info.get('trailingPE'):.2f}" if info.get("trailingPE") else "N/A",
            f"{info.get('priceToBook'):.2f}" if info.get("priceToBook") else "N/A",
            f"{info.get('enterpriseToEbitda'):.2f}" if info.get("enterpriseToEbitda") else "N/A",
            f"{info.get('enterpriseToRevenue'):.2f}" if info.get("enterpriseToRevenue") else "N/A",
            f"{info.get('profitMargins')*100:.2f}" if info.get("profitMargins") else "N/A",
        ]
    except Exception as e:
        print(f"Yahoo Finance verisi alınamadı: {e}")
        yahoo_row = ["Güncel Çarpanlar"] + ["N/A"]*5

    # Renk Fonksiyonu
    RED, GREEN, RESET = "\033[91m", "\033[92m", "\033[0m"
    def colorize(val, median, is_eps=False, is_percent=False):
        num = safe_float(val.replace("%", "")) if isinstance(val, str) else safe_float(val)
        if num is None or median == "N/A":
            return val
        if is_eps:
            colored = f"{GREEN}{val}{RESET}" if num >= median else f"{RED}{val}{RESET}"
        else:
            colored = f"{GREEN}{val}{RESET}" if num <= median else f"{RED}{val}{RESET}"
        return colored + "%" if is_percent else colored

    colored_yahoo_row = [yahoo_row[0]]
    for i, val in enumerate(yahoo_row[1:], start=1):
        colored_yahoo_row.append(colorize(val, medians[i-1], is_eps=(i==5), is_percent=(i==5)))

    # 6. 10 Yıllık CAGR Hesapla
    try:
        # 10 yıl önce ve bugün
        start_date = (datetime.now() - timedelta(days=365*10)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")
        
        # Hisse ve USDTRY verisi
        data_tup = yf.download(f"{stock_code}.IS", start=start_date, end=end_date, progress=False)
        data_usd = yf.download("USDTRY=X", start=start_date, end=end_date, progress=False)
        data_usd_today = yf.download("USDTRY=X", period="1d", progress=False)
        
        # 10 yıl önce USD bazlı fiyat
        tl_close_10y = get_price(data_tup)
        usd_close_10y = get_price(data_usd)
        usd_price_10y = tl_close_10y / usd_close_10y if tl_close_10y and usd_close_10y else None

        # Bugünkü USD bazlı fiyat
        tl_close_today = get_price(yf.download(f"{stock_code}.IS", period="1d", progress=False))
        usd_today = get_price(data_usd_today)
        usd_price_today = tl_close_today / usd_today if tl_close_today and usd_today else None

        # CAGR hesapla
        if usd_price_10y and usd_price_today:
            cagr = (usd_price_today / usd_price_10y) ** (1/10) - 1
        else:
            cagr = 0
    except Exception as e:
        print(f"CAGR hesaplanamadı: {e}")
        cagr = 0

    # 7. Tablo ve GPT Analizi
    final_table = [med_row, colored_yahoo_row]

    genai.configure(api_key=GENAI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')

    headers_tab = ["Karşılaştırma Ölçütü", "Fiyat/Kazanç", "PD/DD", "FD/FAVÖK", "FD/Satış", "Net Kâr Marjı(Yıllıklandırılmış)"]
    table_str = tabulate(final_table, headers=headers_tab, tablefmt="grid")

    prompt = f"""
Aşağıdaki finansal tabloda {stock_code} şirketinin geçmiş 8 yılındaki çarpanlarının MEDYAN değerleri ile Güncel Çarpanlar karşılaştırılmıştır:

{table_str}

Çarpanlar arasındaki olası tutarsızlıkların potansiyel nedenleri ve bu durumun nasıl yorumlanması gerektiğini yaz. Ayrıca hisse senedinin 10 yıllık USD bazlı CAGR (% {cagr*100:.2f}) analizini de dahil et. Analiz Türkçe, kısa ve maddeler halinde olmalı.
""".strip()

    try:
        response = model.generate_content(prompt)
        gpt_text = getattr(response, "text", "GPT yanıtı alınamadı")
    except Exception as e:
        gpt_text = f"GPT analizi başarısız oldu: {e}"

    # 8. Çıktı
    print("\n=== MEDYAN vs Güncel Çarpanlar ===")
    print(tabulate(final_table, headers=headers_tab, tablefmt="grid"))
    print(f"\n📊 {stock_code} 10 Yıllık CAGR ($) : {cagr*100:.2f}%\n")
    print("------------------------------------------------- GPT-4 Analizi --------------------------------------------------------\n")
    print(gpt_text)


# ---------------- Main ----------------
if __name__ == "__main__":
    stock_Code = input("Lütfen analiz edilecek hisse kodunu girin (örn. TUPRS): ").strip().upper()
    analyze_stock(stock_Code)
