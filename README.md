# Hisse Analiz Aracı

Bu Python projesi, Türkiye borsası hisselerinin finansal çarpanlarını ve net kâr marjlarını analiz eder. Aynı zamanda 10 yıllık USD bazlı CAGR hesaplar ve OpenAI GPT modelini kullanarak özet yorum üretir.

---

## Özellikler

- Scorecard web sayfasından finansal verileri çekme
- Net kâr marjı ve çeşitli çarpanların geçmiş 8 yıllık medyanını hesaplama
- Güncel çarpanları Yahoo Finance verileri ile karşılaştırma
- 10 yıllık USD bazlı CAGR hesaplama
- GPT analizi ile kısa ve öz yorum oluşturma
- Terminalde renkli çıktı ile medyan karşılaştırması

---

## Kurulum

1. Python 3.10 veya üzeri yüklü olmalı.
2. Gerekli kütüphaneleri yükleyin:

```bash
pip install -r requirements.txt
```
3. .env dosyası oluşturun ve içine şu değişkenleri ekleyin:
   
**GENAI_API_KEY**=your_openai_api_key

**SCORECARD_URL**=https://analizim.halkyatirim.com.tr/Financial/ScoreCardDetail

---

## Notlar

- `.env` dosyası **asla GitHub’a yüklenmemelidir**.
- PowerShell veya terminalde Python 3.10+ kullanılması önerilir.
- Yahoo Finance ve Scorecard sayfası veri yapısı değişirse, scraping kısmında güncelleme gerekebilir.

**_Yatırım kararlarınızı verirken sadece buraya bağlı kalmayın_**


## Örnek Çıktı

<img width="1772" height="864" alt="image" src="https://github.com/user-attachments/assets/dc456010-b42b-43be-9d8a-1aeb71956cc9" />

---


