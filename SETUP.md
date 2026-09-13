# TLQ Prof Series — Lead Research Bot

Bot otomatis riset perusahaan Jabodetabek yang potential buat TLQ Prof Series, generate email draft, kirim ke Telegram jam 6 pagi WIB.

## Cara Kerja

1. **Scan 8 media bisnis Indonesia** (Detik Finance, Kontan, CNBC Indonesia, Bisnis Indonesia, Kompas Bisnis, Republika Ekonomi, Investor Daily, IDN Finance) 24 jam terakhir
2. **Filter berita** dengan 3 kriteria:
   - Industry fit (perbankan syariah, RS Islam, sekolah Islam, F&B halal, dll)
   - Corporate signal (hiring, transformasi, training, direktur baru, dll)
   - Lokasi Jabodetabek
3. **Ranking + ambil top 5** berdasarkan total score
4. **Generate email draft** siap kirim untuk tiap lead
5. **Kirim ke Telegram** — lo customize + kirim manual dari Gmail lo

## Setup

Setup sama persis dengan viral news bot yang udah lo bikin. Yang beda cuma:

### 1. Bikin Bot Telegram Baru

Chat ke @BotFather → `/newbot` → nama misal "TLQ Leads Bot" → username misal `tlq_leads_rofina_bot` → simpan token.

### 2. Chat ID Sama

Chat ID lo tetep `714948541` (personal Telegram lo), ga perlu ambil baru.

### 3. Upload ke GitHub

Repository baru (misal `tlq-leads-bot`), upload 3 file: `main.py`, `requirements.txt`, `railway.json`.

### 4. Deploy ke Railway

Project baru, connect ke GitHub repo baru.

**Environment Variables:**

| Name | Value |
|------|-------|
| `TELEGRAM_BOT_TOKEN` | Token bot Leads yang baru |
| `TELEGRAM_CHAT_ID` | `714948541` |
| `FOUNDER_NAME` | `Rezha Rendy` |
| `FOUNDER_TITLE` | `Founder, The Living Quran` |
| `FOUNDER_CONTACT` | `thelivingquran.id` |
| `MAX_LEADS_PER_DAY` | `5` |

**Cron Schedule:**
```
0 23 * * *
```
(Jam 6 pagi WIB)

## Workflow Harian Lo

**Setiap pagi jam 6 (~10 menit):**
1. Terima pesan dari bot di Telegram
2. Baca 5 leads → pilih 2-3 yang paling menarik berdasarkan gut feel
3. **LinkedIn search 2 menit per lead**: cari nama HR Director / Kepala HRD perusahaan tsb
4. Copy email draft dari Telegram → customize (ganti "Ibu/Bapak HRD" dengan nama PIC yang ditemukan) → paste ke Gmail
5. Kirim
6. Log ke Google Sheet tracking (nama perusahaan, tanggal kirim, status)

**Follow-up rutin:**
- H+3 sejak kirim: kalau belum reply, follow-up singkat
- H+7: follow-up terakhir dengan value add (share testimonial)
- H+14: move to "cold" list, retry 3 bulan lagi

## Yang Bot GAK Lakuin

- ❌ Auto-kirim email (lo yang kirim manual dari Gmail)
- ❌ Scrape data pribadi (cuma info publik)
- ❌ Simpen database kontak

Ini design intentional — biar legal 100%, brand TLQ aman, response rate tinggi.

## Customization

**Tambah/kurangi industri prioritas:**
Edit `INDUSTRY_KEYWORDS` di `main.py`, adjust score weight.

**Tambah/kurangi signal keywords:**
Edit `SIGNAL_KEYWORDS`. Angka = weight (semakin tinggi = semakin prioritas).

**Ubah lokasi target:**
Edit `JABODETABEK_KEYWORDS` dan `JAKARTA_HQ_COMPANIES`. Kalau mau ekspansi ke Surabaya, tambah keyword surabaya + list perusahaan HQ Surabaya.

**Ubah frekuensi:**
Di Railway → Settings → Cron Schedule. Contoh:
- `0 23 * * *` = jam 6 pagi WIB (default)
- `0 23,6 * * *` = jam 6 pagi + jam 1 siang WIB
- `0 23 * * 1-5` = cuma weekday (Senin-Jumat)

## Troubleshooting

**Ga ada lead yang masuk:**
- Normal kalau weekend / libur nasional (berita bisnis sepi)
- Kalau berturut-turut 3 hari kosong, coba turunin threshold (edit `find_leads()` di `main.py`, ubah `if scores['industry'] < 3` jadi `< 2`)

**Terlalu banyak lead irrelevant:**
- Naikkan threshold: `if scores['industry'] < 5`
- Atau kurangi score weight di INDUSTRY_KEYWORDS untuk industri yang ga match

**Email draft-nya kaku:**
- Edit function `generate_email_draft()` di `main.py`
- Adjust bahasa, tambah spesifik konteks TLQ

## Tips

1. **Bulan 1 fokus quality, bukan quantity.** 5 email personal + follow-up konsisten > 100 email masal.
2. **Track semuanya di Google Sheet.** Pattern akan muncul dalam 2-3 bulan (industri apa yang paling responsive, angle apa yang paling ngena).
3. **Kalau ada yang reply positif**, jangan langsung pitch. Ajak call dulu buat understand kebutuhan mereka.
4. **Testimoni dari lead sebelumnya** adalah senjata terkuat. Update file `main.py` di `generate_email_draft` dengan quote testimoni sekali lo dapet client corporate pertama.
