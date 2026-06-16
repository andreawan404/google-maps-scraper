# scripts/ — CLI Entry Point

## Tanggung Jawab
`main.py` adalah satu-satunya entry point untuk user. Semua logic ada di `src/` — scripts hanya orchestrate.

File ini **sudah ada** di root project (`main.py`) — **pindahkan ke sini tanpa modifikasi**.

---

## Commands yang Tersedia

| Command | Fungsi |
|---------|--------|
| `scrape` | Buka Google Maps, scrape bisnis, simpan ke DB |
| `enrich` | Post-process: cari email + normalisasi phone |
| `export` | Export DB ke CSV |
| `stats` | Tampilkan statistik DB |

---

## Cara Jalankan

```bash
# Dari root project
python scripts/main.py --help
python scripts/main.py scrape --keyword "apotek" --location "Bandung" --max-results 200

# Scrape + langsung export
python scripts/main.py scrape -k "distributor beras" -l "Surabaya" -n 500 --export

# Export saja (data sudah ada di DB)
python scripts/main.py export -o output/apotek_bandung.csv

# Hanya export yang punya kontak
python scripts/main.py export --with-contact-only

# Enrichment terpisah
python scripts/main.py enrich
python scripts/main.py enrich --email-only
python scripts/main.py enrich --phone-only

# Statistik
python scripts/main.py stats
```

---

## Aturan untuk main.py

- **Tidak ada logic bisnis** — hanya Click decorators + `asyncio.run()` + import dari `src/`
- Import dari `src/` dilakukan di **dalam fungsi** (bukan top-level) untuk startup yang cepat
- Semua exception ditangkap di level command, di-print ke user, dan `sys.exit(1)`
- `KeyboardInterrupt` ditangkap khusus dengan pesan yang informatif (data tidak hilang)
- Progress indicator setiap 10 records (`if collected % 10 == 0: click.echo(...)`)

---

## Exit Codes

| Code | Kondisi |
|------|---------|
| 0 | Sukses |
| 1 | Error umum (exception tidak terduga) |
| 2 | CAPTCHA terdeteksi |

---

## Menambah Command Baru

```python
@cli.command()
@click.option("--option", help="Deskripsi option")
def new_command(option: str):
    """Deskripsi singkat command (muncul di --help)."""
    # Import di sini, bukan di top-level
    from src.module.file import function
    function(option)
```
