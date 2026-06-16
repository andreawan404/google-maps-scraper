"""
CLI Entry Point — Google Maps Business Scraper
Jalankan: python scripts/main.py --help
"""
import sys
from pathlib import Path

# Tambahkan project root ke sys.path agar import config/ dan src/ bisa ditemukan
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Set stdout ke UTF-8 agar tidak crash di Windows console CP1252
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import asyncio
from typing import Optional

import click

from config.settings import settings
from src.utils.logger import logger


@click.group()
def cli():
    """Google Maps Business Scraper - Kumpulkan data bisnis untuk marketing & sales."""
    pass


# ─────────────────────────────────────────────────────────────────────────────
# COMMAND: scrape
# ─────────────────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--keyword", "-k", required=True, help="Kata kunci pencarian (contoh: 'distributor beras')")
@click.option("--location", "-l", required=True, help="Lokasi/kota (contoh: 'Surabaya')")
@click.option("--max-results", "-n", default=100, show_default=True, help="Maksimum hasil")
@click.option("--export", "do_export", is_flag=True, default=False, help="Export CSV setelah selesai")
@click.option("--no-enrich", is_flag=True, default=False, help="Skip email enrichment")
@click.option("--proxy", default=None, help="Proxy URL override")
@click.option("--output", "-o", default=None, help="Path CSV output (jika --export)")
def scrape(
    keyword: str,
    location: str,
    max_results: int,
    do_export: bool,
    no_enrich: bool,
    proxy: Optional[str],
    output: Optional[str],
):
    """Scrape data bisnis dari Google Maps."""
    click.echo(f"\n[SCRAPE] '{keyword}' di '{location}' (max: {max_results})")
    click.echo("=" * 55)

    try:
        asyncio.run(_run_scrape(keyword, location, max_results, proxy, not no_enrich, do_export, output))
    except KeyboardInterrupt:
        click.echo("\n[STOP] Dihentikan oleh user. Data tersimpan di DB.")
        sys.exit(0)
    except Exception as e:
        click.echo(f"\n[ERROR] {e}", err=True)
        logger.exception("Scrape command failed")
        sys.exit(1)


async def _run_scrape(
    keyword: str,
    location: str,
    max_results: int,
    proxy: Optional[str],
    do_enrich: bool,
    do_export: bool,
    output_path: Optional[str],
):
    from src.scraper.maps_scraper import scrape_google_maps, CaptchaError
    from src.storage.repository import BusinessRepository
    from src.utils.proxy_manager import proxy_manager

    repo = BusinessRepository()
    collected = 0
    skipped = 0

    active_proxy = proxy or await proxy_manager.next_proxy()

    try:
        async for business in scrape_google_maps(
            keyword=keyword,
            location=location,
            max_results=max_results,
            proxy=active_proxy,
        ):
            if repo.exists(business.place_id):
                skipped += 1
                logger.debug("Skip duplicate: {}", business.name)
                continue

            repo.upsert(business)
            collected += 1

            if collected % 10 == 0:
                click.echo(f"  [{collected}] bisnis terkumpul...")

    except CaptchaError:
        click.echo("\n[CAPTCHA] Terdeteksi! Scraping dihentikan.", err=True)
        sys.exit(2)

    click.echo(f"\n[OK] Scraping selesai: {collected} baru, {skipped} duplikat dilewati")

    if do_enrich:
        await _run_enrich_pipeline(repo)

    if do_export:
        _run_export(output_path)


# ─────────────────────────────────────────────────────────────────────────────
# COMMAND: enrich
# ─────────────────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--email-only", is_flag=True, default=False, help="Hanya cari email")
@click.option("--phone-only", is_flag=True, default=False, help="Hanya normalisasi phone")
def enrich(email_only: bool, phone_only: bool):
    """Jalankan enrichment: cari email dari website & normalisasi phone."""
    click.echo("\n[ENRICH] Menjalankan enrichment pipeline...")

    from src.storage.repository import BusinessRepository

    repo = BusinessRepository()
    asyncio.run(_run_enrich_pipeline(repo, email_only=email_only, phone_only=phone_only))


async def _run_enrich_pipeline(
    repo,
    email_only: bool = False,
    phone_only: bool = False,
):
    from src.enrichment.email_finder import find_emails_for_businesses
    from src.enrichment.phone_normalizer import normalize_phones_batch

    if not phone_only:
        pending = repo.get_without_email()
        click.echo(f"  [EMAIL] Mencari email untuk {len(pending)} bisnis yang punya website...")

        if pending:
            email_map = await find_emails_for_businesses(pending)
            found = sum(1 for e in email_map.values() if e)
            for place_id, email in email_map.items():
                repo.update_email(place_id, email)
            click.echo(f"  [OK] Email ditemukan: {found}/{len(pending)}")

    if not email_only:
        pending_phones = repo.get_without_normalized_phone()
        click.echo(f"  [PHONE] Normalisasi untuk {len(pending_phones)} records...")

        if pending_phones:
            phone_map = normalize_phones_batch(pending_phones)
            for place_id, normalized in phone_map.items():
                repo.update_phone_normalized(place_id, normalized)
            normalized_count = sum(1 for p in phone_map.values() if p)
            click.echo(f"  [OK] Phone dinormalisasi: {normalized_count}/{len(pending_phones)}")


# ─────────────────────────────────────────────────────────────────────────────
# COMMAND: export
# ─────────────────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--output", "-o", default=None, help="Path file CSV output")
@click.option("--with-contact-only", is_flag=True, default=False, help="Hanya export yang punya email/phone")
def export(output: Optional[str], with_contact_only: bool):
    """Export data dari database ke CSV."""
    _run_export(output, with_contact_only)


def _run_export(output_path: Optional[str] = None, with_contact_only: bool = False):
    from src.storage.csv_exporter import export_to_csv
    count = export_to_csv(output_path, only_with_contact=with_contact_only)
    if count > 0:
        click.echo(f"[OK] {count:,} records berhasil diekspor")


# ─────────────────────────────────────────────────────────────────────────────
# COMMAND: stats
# ─────────────────────────────────────────────────────────────────────────────

@cli.command()
def stats():
    """Tampilkan statistik database."""
    from src.storage.repository import BusinessRepository

    repo = BusinessRepository()
    s = repo.get_stats()

    click.echo("\n" + "=" * 45)
    click.echo("   [STATS] Database")
    click.echo("=" * 45)
    click.echo(f"  Total records    : {s['total']:,}")
    click.echo(f"  Punya email      : {s['with_email']:,} ({s['email_coverage']})")
    click.echo(f"  Punya phone      : {s['with_phone']:,} ({s['phone_coverage']})")
    click.echo(f"  Punya website    : {s['with_website']:,}")
    click.echo(f"  Email checked    : {s['email_checked']:,}")
    click.echo("=" * 45 + "\n")


if __name__ == "__main__":
    cli()
