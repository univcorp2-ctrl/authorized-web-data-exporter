from __future__ import annotations

import asyncio
import json
from pathlib import Path

from rich.console import Console

from authorized_web_exporter.config import load_credentials, load_profile
from authorized_web_exporter.crawler import GenericCrawler
from authorized_web_exporter.dashboard import write_dashboard
from authorized_web_exporter.investment_analysis import export_investment_analysis, load_records_jsonl
from authorized_web_exporter.models import DataRecord


class BatchRunError(RuntimeError):
    """Raised when a batch run cannot be started."""


def discover_profile_paths(profile_dir: Path, include: list[str] | None = None) -> list[Path]:
    if not profile_dir.exists():
        raise FileNotFoundError(f"profile_dir not found: {profile_dir}")
    paths = sorted(profile_dir.glob("*.yml")) + sorted(profile_dir.glob("*.yaml"))
    if include:
        include_set = {name.removesuffix(".yml").removesuffix(".yaml") for name in include}
        paths = [path for path in paths if path.stem in include_set]
    return paths


def merge_records(profile_output_dirs: list[Path], combined_dir: Path) -> list[DataRecord]:
    combined_dir.mkdir(parents=True, exist_ok=True)
    records: list[DataRecord] = []
    seen_urls: set[str] = set()
    for output_dir in profile_output_dirs:
        records_path = output_dir / "records.jsonl"
        if not records_path.exists():
            continue
        for record in load_records_jsonl(records_path):
            if record.source_url in seen_urls:
                continue
            records.append(record)
            seen_urls.add(record.source_url)
    with (combined_dir / "records.jsonl").open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
    return records


async def run_batch_profiles(
    profile_dir: Path,
    output_root: Path,
    include: list[str] | None = None,
    generate_analysis: bool = True,
    enable_api_comparison: bool = True,
    console: Console | None = None,
) -> dict[str, object]:
    console = console or Console()
    paths = discover_profile_paths(profile_dir, include=include)
    if not paths:
        raise BatchRunError(f"No profiles found in {profile_dir}")

    output_root.mkdir(parents=True, exist_ok=True)
    profile_output_dirs: list[Path] = []
    results: list[dict[str, object]] = []

    for path in paths:
        profile = load_profile(path)
        profile_output_dir = output_root / profile.name
        profile_output_dirs.append(profile_output_dir)
        try:
            username, password = load_credentials(profile)
            crawler = GenericCrawler(
                profile,
                profile_output_dir,
                username,
                password,
                console=console,
                generate_analysis=False,
                enable_api_comparison=enable_api_comparison,
            )
            console.print(f"[bold cyan]batch source start:[/bold cyan] {profile.name}")
            await crawler.run()
            results.append({"profile": profile.name, "status": "ok", "output_dir": str(profile_output_dir)})
        except Exception as exc:
            results.append(
                {"profile": profile.name, "status": "error", "error": str(exc), "output_dir": str(profile_output_dir)}
            )
            console.print(f"[red]batch source failed:[/red] {profile.name}: {exc}")

    combined_dir = output_root / "_combined"
    records = merge_records(profile_output_dirs, combined_dir)
    summary: dict[str, object] = {
        "profiles_total": len(paths),
        "profiles_ok": sum(1 for item in results if item["status"] == "ok"),
        "profiles_error": sum(1 for item in results if item["status"] == "error"),
        "records_total": len(records),
        "combined_dir": str(combined_dir),
        "results": results,
    }
    if generate_analysis:
        analysis = export_investment_analysis(combined_dir, records, enable_api=enable_api_comparison)
        dashboard_path = write_dashboard(combined_dir / "dashboard", analysis.rows, analysis.summary)
        summary["analysis_summary"] = analysis.summary
        summary["dashboard_path"] = str(dashboard_path)
    (output_root / "batch_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def run_batch(
    profile_dir: Path,
    output_root: Path,
    include: list[str] | None = None,
    generate_analysis: bool = True,
    enable_api_comparison: bool = True,
    console: Console | None = None,
) -> dict[str, object]:
    return asyncio.run(
        run_batch_profiles(
            profile_dir=profile_dir,
            output_root=output_root,
            include=include,
            generate_analysis=generate_analysis,
            enable_api_comparison=enable_api_comparison,
            console=console,
        )
    )
