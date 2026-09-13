#!/usr/bin/env python3
"""
TLQ Prof Series - Daily Lead Research Bot
Scan berita bisnis Indonesia, deteksi corporate signals,
generate lead + email template, kirim ke Telegram.
"""
import os
import re
import time
import requests
import feedparser
from datetime import datetime
from collections import defaultdict
import pytz

# ============================================================
# CONFIGURATION - Set via Railway environment variables
# ============================================================
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')

# Nama founder untuk email signature
FOUNDER_NAME = os.getenv('FOUNDER_NAME', 'Rezha Rendy')
FOUNDER_TITLE = os.getenv('FOUNDER_TITLE', 'Founder, The Living Quran')
FOUNDER_CONTACT = os.getenv('FOUNDER_CONTACT', 'thelivingquran.id')

# Jumlah lead max per hari
MAX_LEADS_PER_DAY = int(os.getenv('MAX_LEADS_PER_DAY', '5'))

# ============================================================
# RSS FEEDS - Berita bisnis Indonesia
# ============================================================
RSS_FEEDS = {
    'Detik Finance': 'https://finance.detik.com/rss',
    'Kontan': 'https://www.kontan.co.id/rss/nasional',
    'CNBC Indonesia': 'https://www.cnbcindonesia.com/news/rss',
    'Bisnis Indonesia': 'https://www.bisnis.com/rss',
    'Kompas Bisnis': 'https://money.kompas.com/rss',
    'Republika Ekonomi': 'https://ekonomi.republika.co.id/rss',
    'Investor Daily': 'https://investor.id/rss',
    'IDN Finance': 'https://www.idntimes.com/business/rss',
}

# ============================================================
# INDUSTRY VALUE-ALIGN SCORING
# Prioritas industri yang natural fit sama TLQ Prof Series
# ============================================================
INDUSTRY_KEYWORDS = {
    # Highest fit (score +5): value-align sangat kuat
    'perbankan syariah': 5, 'bank syariah': 5, 'bsi': 5, 'muamalat': 5,
    'asuransi syariah': 5, 'takaful': 5, 'fintech syariah': 5,
    'pesantren': 5, 'sekolah islam': 5, 'universitas islam': 5,
    'uin ': 5, 'iain ': 5, 'stain ': 5, 'unida': 5,
    'rumah sakit islam': 5, 'rs islam': 5, 'rsi ': 5, 'rsia': 5,
    'muhammadiyah': 5, 'nu ': 5, 'nahdlatul ulama': 5,
    'baznas': 5, 'lazismu': 5, 'lazisnu': 5, 'dompet dhuafa': 5,
    'halal': 5, 'zakat': 5, 'wakaf': 5, 'umroh': 5, 'haji': 5,

    # High fit (score +3): muslim-majority workforce
    'kosmetik halal': 3, 'wardah': 3, 'paragon': 3,
    'makanan halal': 3, 'restoran halal': 3, 'f&b halal': 3,
    'kementerian agama': 3, 'kemenag': 3,
    'pendidikan': 3, 'sekolah': 3, 'universitas': 3, 'kampus': 3,
    'rumah sakit': 3, 'klinik': 3, 'healthcare': 3,

    # Medium fit (score +2): general corporate yang possible
    'bank': 2, 'perbankan': 2, 'asuransi': 2,
    'bumn': 2, 'bumd': 2,
    'perusahaan': 2, 'korporasi': 2,
}

# ============================================================
# SIGNAL KEYWORDS - Trigger yang nandain corporate opportunity
# ============================================================
SIGNAL_KEYWORDS = {
    # Highest signal (score +5): timing perfect buat pitch
    'transformasi budaya': 5, 'culture transformation': 5,
    'character building': 5, 'pembentukan karakter': 5,
    'program pengembangan sdm': 5, 'people development': 5,
    'employee wellbeing': 5, 'kesejahteraan karyawan': 5,
    'retret': 5, 'spiritual': 5, 'mentoring karyawan': 5,

    # High signal (score +3): fase perubahan = butuh tools
    'ekspansi': 3, 'expansion': 3, 'buka kantor': 3,
    'hiring': 3, 'lowongan': 3, 'rekrut': 3, 'rekrutmen': 3,
    'onboarding': 3, 'orientasi': 3,
    'direktur sdm': 3, 'direktur hrd': 3, 'chief people officer': 3,
    'cpo baru': 3, 'hr director': 3, 'kepala hrd': 3,
    'training': 3, 'pelatihan': 3, 'workshop': 3,
    'restrukturisasi': 3, 'reorganisasi': 3,

    # Medium signal (score +2): general corporate news
    'peluncuran': 2, 'launch': 2, 'meluncurkan': 2,
    'kerja sama': 2, 'kolaborasi': 2, 'kemitraan': 2,
    'csr': 2, 'tanggung jawab sosial': 2,
    'anniversary': 2, 'hut ke': 2, 'ulang tahun': 2,
    'penghargaan': 2, 'award': 2, 'apresiasi': 2,
}

# ============================================================
# JABODETABEK FILTER - Lokasi target
# ============================================================
JABODETABEK_KEYWORDS = {
    'jakarta', 'jkt', 'dki',
    'bogor', 'depok', 'tangerang', 'tangsel', 'bekasi',
    'jabodetabek', 'jabodetabekjur', 'greater jakarta',
    'bsd', 'sudirman', 'thamrin', 'kuningan', 'senayan', 'menteng',
    'kemayoran', 'kelapa gading', 'kebayoran', 'pondok indah',
    'cempaka putih', 'cikarang', 'karawaci', 'serpong', 'alam sutera',
}

# Perusahaan besar yang HQ-nya di Jabodetabek (whitelist)
JAKARTA_HQ_COMPANIES = {
    'bank mandiri', 'bri', 'bni', 'bca', 'bsi', 'btn',
    'bank muamalat', 'bank mega syariah', 'cimb niaga',
    'pertamina', 'telkom', 'pln', 'garuda indonesia',
    'astra', 'gojek', 'goto', 'tokopedia', 'traveloka', 'bukalapak',
    'sinar mas', 'salim group', 'lippo', 'ciputra',
    'unilever indonesia', 'indofood', 'mayora', 'wings',
    'paragon', 'wardah', 'kalbe farma', 'kimia farma',
    'takaful', 'prudential syariah', 'allianz syariah',
    'kemenag', 'baznas', 'dompet dhuafa', 'rumah zakat',
}


def log(msg):
    """Print dengan timestamp WIB"""
    wib = pytz.timezone('Asia/Jakarta')
    now = datetime.now(wib).strftime('%H:%M:%S')
    print(f"[{now}] {msg}", flush=True)


def fetch_feed(source_name, url, timeout=15):
    """Ambil satu RSS feed"""
    try:
        headers = {
            'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                           'AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/120.0.0.0 Safari/537.36'),
            'Accept': 'application/rss+xml, application/xml, text/xml, */*',
            'Accept-Language': 'id-ID,id;q=0.9,en;q=0.8',
        }
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        feed = feedparser.parse(r.content)
        return feed.entries
    except Exception as e:
        log(f"  x {source_name}: {str(e)[:80]}")
        return []


def fetch_all_news():
    """Ambil berita dari semua sumber"""
    all_articles = []
    for source, url in RSS_FEEDS.items():
        entries = fetch_feed(source, url)
        count = 0
        for entry in entries[:40]:
            title = entry.get('title', '').strip()
            summary = entry.get('summary', '') or entry.get('description', '')
            link = entry.get('link', '').strip()
            if title and link:
                # Strip HTML dari summary
                summary_clean = re.sub(r'<[^>]+>', ' ', summary).strip()[:500]
                all_articles.append({
                    'title': title,
                    'summary': summary_clean,
                    'link': link,
                    'source': source,
                    'full_text': (title + ' ' + summary_clean).lower(),
                })
                count += 1
        if count > 0:
            log(f"  v {source}: {count} artikel")
    return all_articles


def score_article(article):
    """Score artikel berdasarkan industry fit + signal strength + location"""
    text = article['full_text']
    scores = {
        'industry': 0,
        'signal': 0,
        'location': 0,
        'industry_matches': [],
        'signal_matches': [],
    }

    # Industry scoring
    for keyword, weight in INDUSTRY_KEYWORDS.items():
        if keyword in text:
            scores['industry'] += weight
            scores['industry_matches'].append(keyword)

    # Signal scoring
    for keyword, weight in SIGNAL_KEYWORDS.items():
        if keyword in text:
            scores['signal'] += weight
            scores['signal_matches'].append(keyword)

    # Location scoring (Jabodetabek)
    for keyword in JABODETABEK_KEYWORDS:
        if keyword in text:
            scores['location'] += 2
            break

    # Whitelist Jakarta HQ companies
    for company in JAKARTA_HQ_COMPANIES:
        if company in text:
            scores['location'] += 3
            scores['industry'] += 2  # boost karena udah tervalidasi
            break

    # Total score (industry paling penting, signal medium, location gating)
    total = scores['industry'] * 2 + scores['signal']
    if scores['location'] == 0:
        total = total * 0.3  # penalize non-Jabodetabek berat

    scores['total'] = total
    scores['fit_stars'] = min(5, max(1, int(total / 5)))

    return scores


def extract_company_name(article):
    """Coba ekstrak nama perusahaan dari judul (heuristic)"""
    title = article['title']

    # Cari pola nama perusahaan: PT XXX, Bank XXX, dll
    patterns = [
        r'(PT [A-Z][A-Za-z\s&]+?)(?:\s+(?:Buka|Rombak|Luncurkan|Adakan|Kirim|Raih|Catat|Umumkan|Gelar|Rekrut|Rencana|Lakukan|Tambah)|\s+ke|\s+di|\s+akan|,|\.)',
        r'(Bank [A-Z][A-Za-z\s]+?)(?:\s+(?:Luncurkan|Adakan|Rombak|Kembangkan|Perkuat|Gelar|Buka|Gandeng)|,|\.)',
        r'(BSI|BRI|BNI|BCA|BTN|Mandiri|Muamalat|Pertamina|Telkom|PLN|Garuda|Astra|Gojek|GoTo|Tokopedia|Bukalapak|Unilever|Indofood|Mayora|Wardah|Paragon|Kalbe|Takaful)',
        r'(RS [A-Z][A-Za-z\s]+?)(?:\s+|,|\.)',
        r'(RSIA [A-Z][A-Za-z\s]+?)(?:\s+|,|\.)',
        r'(Universitas [A-Z][A-Za-z\s]+?)(?:\s+|,|\.)',
        r'(UIN [A-Z][A-Za-z\s]+?)(?:\s+|,|\.)',
        r'(Kementerian [A-Z][A-Za-z\s]+?)(?:\s+|,|\.)',
    ]

    for pattern in patterns:
        match = re.search(pattern, title)
        if match:
            return match.group(1).strip()

    # Fallback: ambil 3 kata pertama yang capitalized
    words = title.split()
    company_words = []
    for w in words[:6]:
        if w[0].isupper() and len(w) > 2:
            company_words.append(w)
        elif company_words:
            break
    if company_words:
        return ' '.join(company_words)

    return title[:50] + '...' if len(title) > 50 else title


def generate_angle(article, scores):
    """Generate suggested angle buat outreach"""
    text = article['full_text']

    # Pattern-based angle generation
    if any(k in text for k in ['transformasi budaya', 'culture transformation']):
        return ("Inisiatif transformasi budaya butuh sustaining tool. Prof Series "
                "= companion harian buat internalisasi values (100 ayat kurasi, 5 menit/hari).")

    if any(k in text for k in ['character building', 'pembentukan karakter']):
        return ("Character building program biasanya kuat di training, drop di practice. "
                "Prof Series design-nya buat gap itu: 1 ayat 1 aksi tiap hari.")

    if any(k in text for k in ['hiring', 'rekrut', 'lowongan', 'onboarding']):
        return ("Fase hiring/onboarding = kesempatan tanamkan value sejak awal. "
                "Prof Series bisa jadi part of onboarding kit karyawan baru.")

    if any(k in text for k in ['direktur sdm', 'direktur hrd', 'hr director', 'cpo baru']):
        return ("HR Director baru biasanya cari signature initiative. Prof Series bisa "
                "positioning sebagai program flagship yang measurable + mudah execute.")

    if any(k in text for k in ['ekspansi', 'buka kantor', 'expansion']):
        return ("Ekspansi = growth phase = butuh scale culture. Prof Series bisa jadi "
                "tool standardisasi values across branches.")

    if any(k in text for k in ['training', 'pelatihan', 'workshop']):
        return ("Post-training biasanya butuh sustaining tool supaya insight ga hilang. "
                "Prof Series design-nya persis untuk itu.")

    if any(k in text for k in ['csr', 'tanggung jawab sosial']):
        return ("CSR yang meaningful biasanya integrate ke internal values. Prof Series "
                "bisa jadi bridge antara CSR external dan culture internal.")

    if any(k in text for k in ['anniversary', 'hut ke', 'ulang tahun']):
        return ("Momen anniversary = timing bagus buat renew culture initiative. Prof "
                "Series bisa jadi gift-with-purpose ke seluruh karyawan.")

    # Default angle
    return ("Prof Series = tool praktis buat transform ayat Al-Qur'an jadi kebiasaan "
            "kerja harian. Sudah dipakai institusi serupa dengan tantangan people development.")


def generate_email_draft(article, company, scores, angle):
    """Generate email draft ready to send"""
    signal_text = article['title']

    email = f"""Assalamu'alaikum Ibu/Bapak HRD {company},

Saya {FOUNDER_NAME} dari The Living Quran. Membaca berita "{signal_text}" \
({article['source']}), saya reach out untuk berbagi insight yang mungkin relevan \
dengan inisiatif yang sedang dijalankan.

Singkatnya: banyak program pengembangan SDM berhasil di fase training, tapi drop \
setelah 2-3 bulan karena tidak ada tool praktik harian. TLQ Prof Series dirancang \
untuk gap itu — 100 ayat Al-Qur'an kurasi tema etos kerja, integritas, leadership, \
komunikasi tim, dengan format "1 ayat 1 aksi" yang bisa dijalankan 5 menit per hari \
per karyawan.

Angle spesifik untuk konteks {company}: {angle}

Boleh saya kirim company profile + brosur produk? Atau kalau berkenan, 20 menit \
video call untuk saya jelaskan lebih konkret bagaimana ini bisa jadi companion \
tool inisiatif tim.

Barakallahu fiikum,

{FOUNDER_NAME}
{FOUNDER_TITLE}
{FOUNDER_CONTACT}
"""
    return email


def build_lead_card(article, company, scores, angle, email_draft, rank):
    """Build satu lead card dalam format Telegram HTML"""
    stars = '⭐' * scores['fit_stars']

    industries = ', '.join(scores['industry_matches'][:3]) if scores['industry_matches'] else '-'
    signals = ', '.join(scores['signal_matches'][:3]) if scores['signal_matches'] else '-'

    card = (
        f"<b>#{rank} · Fit Score: {stars} ({scores['fit_stars']}/5)</b>\n\n"
        f"🏢 <b>{company}</b>\n\n"
        f"📰 <b>SIGNAL:</b>\n"
        f"<i>\"{article['title'][:200]}\"</i>\n"
        f"({article['source']})\n\n"
        f"💡 <b>WHY FIT:</b>\n"
        f"· Industry match: {industries}\n"
        f"· Corporate signal: {signals}\n\n"
        f"🎣 <b>ANGLE OUTREACH:</b>\n"
        f"<i>{angle}</i>\n\n"
        f"🔗 <a href=\"{article['link']}\">Baca berita lengkap</a>\n\n"
        f"📧 <b>EMAIL DRAFT (copy-paste):</b>\n"
        f"<code>{email_draft}</code>\n"
    )
    return card


def find_leads(articles):
    """Filter + rank artikel jadi top leads"""
    scored = []
    seen_companies = set()

    for article in articles:
        scores = score_article(article)

        # Filter: harus punya minimal industry fit + signal + Jabodetabek
        if scores['industry'] < 3:
            continue
        if scores['signal'] < 3:
            continue
        if scores['location'] == 0:
            continue

        company = extract_company_name(article)

        # Dedup: 1 perusahaan max 1 lead per hari
        company_key = company.lower()[:30]
        if company_key in seen_companies:
            continue
        seen_companies.add(company_key)

        angle = generate_angle(article, scores)
        email_draft = generate_email_draft(article, company, scores, angle)

        scored.append({
            'article': article,
            'company': company,
            'scores': scores,
            'angle': angle,
            'email_draft': email_draft,
        })

    # Sort by total score desc
    scored.sort(key=lambda x: x['scores']['total'], reverse=True)

    return scored[:MAX_LEADS_PER_DAY]


def send_telegram(text):
    """Kirim pesan ke Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log("⚠️  TELEGRAM_BOT_TOKEN atau TELEGRAM_CHAT_ID belum di-set!")
        print("\n" + text + "\n")
        return False

    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': text,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True,
    }
    try:
        r = requests.post(url, json=payload, timeout=15)
        if r.status_code != 200:
            log(f"  x Telegram error {r.status_code}: {r.text[:200]}")
            return False
        return True
    except Exception as e:
        log(f"  x Telegram exception: {e}")
        return False


def build_header(now, total_articles, num_leads):
    """Header pesan"""
    return (
        f"🎯 <b>TLQ PROF SERIES — DAILY LEADS</b>\n"
        f"📅 {now.strftime('%A, %d %B %Y')}\n"
        f"⏰ {now.strftime('%H:%M WIB')}\n"
        f"📊 Scan {total_articles} berita 24 jam terakhir\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Ditemukan <b>{num_leads} lead potensial</b>\n"
        f"Filter: Jabodetabek + Industry Fit + Timing Signal\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    )


def build_no_leads_message(now, total_articles):
    """Message kalau ga ada lead"""
    return (
        f"🎯 <b>TLQ PROF SERIES — DAILY LEADS</b>\n"
        f"📅 {now.strftime('%A, %d %B %Y')}\n"
        f"⏰ {now.strftime('%H:%M WIB')}\n\n"
        f"📊 Sudah scan {total_articles} berita 24 jam terakhir\n\n"
        f"⚠️ <b>Hari ini belum ada lead yang match</b>\n"
        f"kriteria: Jabodetabek + Industry Fit + Timing Signal\n\n"
        f"💡 <b>Rekomendasi:</b>\n"
        f"Hari sepi berita corporate. Bagus buat:\n"
        f"· Follow-up leads dari hari sebelumnya\n"
        f"· Deepen relationship dengan lead yang udah reply\n"
        f"· Review pipeline\n\n"
        f"Bot lanjut scan besok jam 6 pagi ⏭️"
    )


def build_footer(leads):
    """Footer summary"""
    if not leads:
        return ""

    industries = defaultdict(int)
    for lead in leads:
        for ind in lead['scores']['industry_matches'][:1]:
            industries[ind] += 1

    industry_summary = ', '.join([f"{count} {ind}" for ind, count in industries.items()])

    return (
        f"\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 <b>SUMMARY:</b>\n"
        f"· {len(leads)} leads dikirim\n"
        f"· Industri: {industry_summary}\n"
        f"· Semua Jabodetabek ✅\n\n"
        f"💡 <b>WORKFLOW:</b>\n"
        f"1. Pilih 2-3 lead paling menarik\n"
        f"2. LinkedIn search PIC HR (2 menit)\n"
        f"3. Customize email draft + kirim\n"
        f"4. Log ke tracking sheet\n\n"
        f"⏭️  Besok jam 6 pagi kirim batch baru"
    )


def main():
    wib = pytz.timezone('Asia/Jakarta')
    now = datetime.now(wib)

    log("=" * 50)
    log("TLQ PROF SERIES - LEAD RESEARCH BOT")
    log(f"Waktu: {now.strftime('%Y-%m-%d %H:%M WIB')}")
    log("=" * 50)

    log("\n📥 Scan berita bisnis Indonesia...")
    articles = fetch_all_news()
    log(f"\n📊 Total artikel: {len(articles)}")

    if not articles:
        log("⚠️  Tidak ada artikel yang berhasil di-fetch!")
        send_telegram(
            f"⚠️ <b>TLQ Lead Bot</b>\n"
            f"🕐 {now.strftime('%H:%M WIB')}\n\n"
            f"Gagal fetch berita. Cek koneksi atau RSS feed."
        )
        return

    log("\n🔍 Analisa + filter leads...")
    leads = find_leads(articles)
    log(f"🎯 Ditemukan {len(leads)} lead potensial")

    for i, lead in enumerate(leads, 1):
        stars = '⭐' * lead['scores']['fit_stars']
        log(f"  {i}. {lead['company']} — {stars} ({lead['scores']['total']:.0f} pts)")

    log("\n📤 Kirim ke Telegram...")

    if not leads:
        send_telegram(build_no_leads_message(now, len(articles)))
        log("\n✅ Selesai (no leads today)")
        return

    # Kirim header
    send_telegram(build_header(now, len(articles), len(leads)))
    time.sleep(1)

    # Kirim tiap lead sebagai pesan terpisah (biar copy email gampang)
    for i, lead in enumerate(leads, 1):
        card = build_lead_card(
            lead['article'],
            lead['company'],
            lead['scores'],
            lead['angle'],
            lead['email_draft'],
            i,
        )

        # Split kalau kepanjangan
        if len(card) > 4000:
            # Split di section email draft
            parts = card.split("📧 <b>EMAIL DRAFT")
            if len(parts) == 2:
                send_telegram(parts[0])
                time.sleep(1)
                send_telegram("📧 <b>EMAIL DRAFT" + parts[1])
            else:
                send_telegram(card[:4000])
                time.sleep(1)
                send_telegram(card[4000:])
        else:
            send_telegram(card)

        time.sleep(1.5)  # rate limit Telegram

    # Footer
    send_telegram(build_footer(leads))

    log("\n✅ Selesai!")


if __name__ == '__main__':
    main()
