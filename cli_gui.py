#!/usr/bin/env python3
"""
Dify Knowledge Base Migration Tool - Interactive CLI GUI

Beautiful and interactive command-line interface for migrating Dify knowledge bases.
"""

import os
import sys
from pathlib import Path
from typing import List, Optional
import warnings

# Suppress SSL warnings when verification is disabled
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import questionary
from questionary import Style
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text
from rich import box
from rich.layout import Layout
from rich.live import Live
from rich.align import Align
from rich.columns import Columns

from dify_migration import (
    DifyMigration,
    DifyConfig,
    DifyClient,
    load_config_from_env,
    load_config_from_json
)

# Rich console for beautiful output
console = Console()

# Custom style for questionary prompts
custom_style = Style([
    ('qmark', 'fg:#00d9ff bold'),       # Cyan question mark
    ('question', 'bold fg:#ffffff'),     # White question
    ('answer', 'fg:#00ff87 bold'),      # Green answer
    ('pointer', 'fg:#00d9ff bold'),     # Cyan pointer
    ('highlighted', 'fg:#00d9ff bold'), # Cyan highlight
    ('selected', 'fg:#00ff87'),         # Green selected
    ('separator', 'fg:#6c6c6c'),        # Gray separator
    ('instruction', 'fg:#858585'),      # Light gray instruction
    ('text', 'fg:#ffffff'),             # White text
])


def print_banner():
    """Print beautiful animated banner with gradient colors"""
    console.print()

    # Main logo with gradient
    logo_lines = [
        "╔═══════════════════════════════════════════════════════════════════════╗",
        "║                                                                       ║",
        "║     ██████╗ ██╗███████╗██╗   ██╗    ███╗   ███╗██╗ ██████╗          ║",
        "║     ██╔══██╗██║██╔════╝╚██╗ ██╔╝    ████╗ ████║██║██╔════╝          ║",
        "║     ██║  ██║██║█████╗   ╚████╔╝     ██╔████╔██║██║██║  ███╗         ║",
        "║     ██║  ██║██║██╔══╝    ╚██╔╝      ██║╚██╔╝██║██║██║   ██║         ║",
        "║     ██████╔╝██║██║        ██║       ██║ ╚═╝ ██║██║╚██████╔╝         ║",
        "║     ╚═════╝ ╚═╝╚═╝        ╚═╝       ╚═╝     ╚═╝╚═╝ ╚═════╝          ║",
        "║                                                                       ║",
        "╚═══════════════════════════════════════════════════════════════════════╝",
    ]

    colors = ["bright_magenta", "magenta", "bright_blue", "blue", "cyan", "bright_cyan", "cyan", "blue", "bright_blue", "magenta"]

    for i, line in enumerate(logo_lines):
        console.print(line, style=f"bold {colors[i]}", justify="center")

    console.print()

    # Title panel with gradient background
    title_panel = Panel(
        Text.assemble(
            ("Knowledge Base Migration Tool ", "bold bright_white"),
            ("v2.1", "bold bright_green"),
            "\n",
            ("🚀 ", "yellow"),
            ("Streaming Edition", "bold bright_cyan"),
            (" 🚀", "yellow"),
        ),
        border_style="bright_magenta",
        box=box.DOUBLE,
        padding=(0, 2),
    )
    console.print(title_panel, justify="center")

    console.print()

    # Feature badges
    features = [
        ("⚡", "bright_yellow", "Lightning Fast"),
        ("💾", "bright_blue", "Memory Efficient"),
        ("🔄", "bright_green", "Real-time Sync"),
        ("📊", "bright_magenta", "Progress Tracking"),
    ]

    feature_text = Text()
    for emoji, color, label in features:
        feature_text.append(f"{emoji} ", style=color)
        feature_text.append(f"{label}", style=f"bold {color}")
        feature_text.append("  │  ", style="dim white")

    # Remove last separator
    feature_text = Text(str(feature_text)[:-5])

    console.print(feature_text, justify="center")
    console.print()


def load_configuration():
    """Load configuration with interactive fallback"""
    with console.status("[bold cyan]📋 Loading Configuration...", spinner="dots"):
        try:
            # Try .env first
            source_configs, target_config = load_config_from_env()
            console.print("✅ Configuration loaded from [green bold].env[/green bold] file")
            return source_configs, target_config
        except (ValueError, FileNotFoundError) as env_error:
            console.print(f"⚠️  .env not found", style="yellow")

            try:
                # Fallback to config.json
                source_configs, target_config = load_config_from_json()
                console.print("✅ Configuration loaded from [green bold]config.json[/green bold] file")
                return source_configs, target_config
            except FileNotFoundError:
                console.print()
                console.print(Panel(
                    "[bold red]❌ No configuration found![/bold red]\n\n"
                    "Please create configuration file:\n"
                    "  [cyan]1. .env file (recommended)[/cyan] - see .env.example\n"
                    "  [cyan]2. config.json[/cyan] - see config.example.json",
                    title="Configuration Error",
                    border_style="red"
                ))

                # Interactive setup
                if questionary.confirm(
                    "Would you like to set up configuration now?",
                    style=custom_style
                ).ask():
                    return interactive_config_setup()
                else:
                    console.print("\n[yellow]Run[/yellow] [cyan bold]./setup.sh[/cyan bold] [yellow]for quick setup[/yellow]\n")
                    sys.exit(1)


def interactive_config_setup():
    """Interactive configuration setup"""
    console.print()
    console.print(Panel(
        "[bold cyan]🔧 Interactive Configuration Setup[/bold cyan]\n\n"
        "I'll guide you through setting up your Dify API keys",
        border_style="cyan"
    ))
    console.print()

    # Source configuration
    source_count = questionary.select(
        "How many source API keys do you have?",
        choices=[
            "1 (Single source)",
            "2 (Two sources)",
            "3 (Three sources)",
            "Custom (enter number)"
        ],
        style=custom_style
    ).ask()

    if source_count == "Custom (enter number)":
        num_sources = int(questionary.text(
            "Enter number of sources:",
            validate=lambda x: x.isdigit() and int(x) > 0,
            style=custom_style
        ).ask())
    else:
        num_sources = int(source_count.split()[0])

    source_base_url = questionary.text(
        "Source Base URL:",
        default="https://api.dify.ai",
        style=custom_style
    ).ask()

    source_configs = []
    for i in range(num_sources):
        console.print(f"\n[bold bright_cyan]Source {i+1}/{num_sources}[/bold bright_cyan]")
        api_key = questionary.password(
            f"  API Key {i+1}:",
            style=custom_style
        ).ask()

        source_configs.append(DifyConfig(
            base_url=source_base_url,
            api_key=api_key
        ))

    # Target configuration
    console.print(f"\n[bold bright_green]Target Configuration[/bold bright_green]")
    target_base_url = questionary.text(
        "Target Base URL:",
        default="https://api.dify.ai",
        style=custom_style
    ).ask()

    target_api_key = questionary.password(
        "Target API Key:",
        style=custom_style
    ).ask()

    target_config = DifyConfig(
        base_url=target_base_url,
        api_key=target_api_key
    )

    # Save to .env?
    if questionary.confirm(
        "Save this configuration to .env file?",
        default=True,
        style=custom_style
    ).ask():
        save_to_env(source_configs, target_config)
        console.print("\n✅ Configuration saved to [green bold].env[/green bold]")

    return source_configs, target_config


def save_to_env(source_configs: List[DifyConfig], target_config: DifyConfig):
    """Save configuration to .env file"""
    source_keys = ','.join([config.api_key for config in source_configs])

    env_content = f"""# Dify Migration Tool Configuration
# Generated by CLI GUI

# Source Dify Instances Configuration
SOURCE_BASE_URL={source_configs[0].base_url}
SOURCE_API_KEYS={source_keys}

# Target Dify Instance Configuration
TARGET_BASE_URL={target_config.base_url}
TARGET_API_KEY={target_config.api_key}
"""

    with open('.env', 'w') as f:
        f.write(env_content)


def show_sources_info(source_configs: List[DifyConfig], target_config: DifyConfig):
    """Display sources information in a beautiful panel with gradients"""

    # Create gradient table
    table = Table(
        show_header=True,
        header_style="bold bright_magenta on black",
        border_style="bright_blue",
        box=box.DOUBLE_EDGE,
        title="✨ Configuration Overview ✨",
        title_style="bold bright_white on black",
        padding=(0, 1),
        expand=False
    )

    table.add_column("🔧 Type", style="bold bright_cyan", no_wrap=True, width=15)
    table.add_column("🌐 Base URL", style="bright_green", width=35)
    table.add_column("🔑 API Key", style="bright_yellow", width=20)
    table.add_column("✅ Status", style="bright_white", width=12, justify="center")

    # Add sources with gradient colors
    source_colors = ["bright_cyan", "cyan", "blue", "bright_blue"]
    for i, config in enumerate(source_configs, 1):
        masked_key = f"{config.api_key[:10]}...{config.api_key[-4:]}" if len(config.api_key) > 14 else config.api_key
        color = source_colors[i % len(source_colors)]
        table.add_row(
            f"📦 Source {i}",
            config.base_url,
            masked_key,
            "🟢 Ready",
            style=color
        )

    # Add separator
    table.add_row("", "", "", "", end_section=True)

    # Add target with special styling
    masked_target = f"{target_config.api_key[:10]}...{target_config.api_key[-4:]}" if len(target_config.api_key) > 14 else target_config.api_key
    table.add_row(
        "🎯 Target",
        target_config.base_url,
        masked_target,
        "🟢 Ready",
        style="bold bright_green"
    )

    # Wrap in panel
    config_panel = Panel(
        table,
        border_style="bright_magenta",
        box=box.DOUBLE,
        padding=(1, 2),
    )

    console.print()
    console.print(config_panel)

    # Show count summary
    summary = Text()
    summary.append("💡 ", style="bright_yellow")
    summary.append(f"{len(source_configs)}", style="bold bright_cyan")
    summary.append(" source(s) → ", style="dim white")
    summary.append("1", style="bold bright_green")
    summary.append(" target", style="dim white")
    console.print(summary, justify="center")
    console.print()


def list_all_datasets(source_configs: List[DifyConfig], target_config: DifyConfig):
    """List all datasets from sources and target with beautiful formatting"""
    console.print()

    # Header with icon
    header = Panel(
        Text.assemble(
            ("📚 ", "bright_yellow"),
            ("Knowledge Base Inventory", "bold bright_white"),
            "\n\n",
            ("Scanning all sources and target for datasets...", "dim cyan"),
        ),
        border_style="bright_magenta",
        box=box.DOUBLE,
        padding=(1, 2),
    )
    console.print(header)
    console.print()

    with Progress(
        SpinnerColumn(spinner_name="dots12", style="bright_cyan"),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True
    ) as progress:
        # Source datasets
        for i, config in enumerate(source_configs, 1):
            task = progress.add_task(f"[bright_cyan]⚡ Scanning Source {i}...", total=None)

            try:
                client = DifyClient(config)
                datasets = client.get_all_datasets()
                progress.remove_task(task)

                # Display source datasets with enhanced styling
                table = Table(
                    title=f"📦 Source {i}",
                    title_style="bold bright_cyan on black",
                    box=box.DOUBLE_EDGE,
                    show_header=True,
                    header_style="bold bright_yellow on black",
                    border_style="bright_blue",
                    padding=(0, 1),
                    caption=f"Total: {len(datasets)} knowledge base(s)",
                    caption_style="dim cyan italic"
                )

                table.add_column("No.", style="bold bright_cyan", width=5, justify="right")
                table.add_column("📚 Dataset Name", style="bold bright_white", min_width=30)
                table.add_column("📄 Docs", justify="center", style="bright_blue", width=8)
                table.add_column("📝 Words", justify="right", style="bright_magenta", width=12)

                for idx, ds in enumerate(datasets, 1):
                    # Color alternation for rows
                    row_style = "on black" if idx % 2 == 0 else ""
                    table.add_row(
                        str(idx),
                        ds['name'],
                        str(ds.get('document_count', 0)),
                        f"{ds.get('word_count', 0):,}",
                        style=row_style
                    )

                # Wrap table in panel
                table_panel = Panel(
                    table,
                    border_style="cyan",
                    box=box.ROUNDED,
                    padding=(0, 1),
                )
                console.print(table_panel)
                console.print()

            except Exception as e:
                progress.remove_task(task)
                console.print(Panel(
                    Text.assemble(
                        ("❌ ", "bold red"),
                        (f"Failed to fetch from Source {i}", "bold red"),
                        ("\n\n", ""),
                        (str(e), "red"),
                    ),
                    border_style="red",
                    box=box.HEAVY
                ))
                console.print()

        # Target datasets with special styling
        task = progress.add_task("[bright_green]⚡ Scanning Target...", total=None)

        try:
            client = DifyClient(target_config)
            datasets = client.get_all_datasets()
            progress.remove_task(task)

            table = Table(
                title=f"🎯 Target Destination",
                title_style="bold bright_green on black",
                box=box.DOUBLE_EDGE,
                show_header=True,
                header_style="bold bright_yellow on black",
                border_style="bright_green",
                padding=(0, 1),
                caption=f"Total: {len(datasets)} knowledge base(s)",
                caption_style="dim green italic"
            )

            table.add_column("No.", style="bold bright_green", width=5, justify="right")
            table.add_column("📚 Dataset Name", style="bold bright_white", min_width=30)
            table.add_column("📄 Docs", justify="center", style="bright_blue", width=8)
            table.add_column("📝 Words", justify="right", style="bright_magenta", width=12)

            for idx, ds in enumerate(datasets, 1):
                row_style = "on black" if idx % 2 == 0 else ""
                table.add_row(
                    str(idx),
                    ds['name'],
                    str(ds.get('document_count', 0)),
                    f"{ds.get('word_count', 0):,}",
                    style=row_style
                )

            # Wrap in panel with green theme
            table_panel = Panel(
                table,
                border_style="green",
                box=box.ROUNDED,
                padding=(0, 1),
            )
            console.print(table_panel)
            console.print()

        except Exception as e:
            progress.remove_task(task)
            console.print(Panel(
                Text.assemble(
                    ("❌ ", "bold red"),
                    ("Failed to fetch from Target", "bold red"),
                    ("\n\n", ""),
                    (str(e), "red"),
                ),
                border_style="red",
                box=box.HEAVY
            ))
            console.print()


def run_migration(source_configs: List[DifyConfig], target_config: DifyConfig):
    """Run full migration with beautiful streaming display"""
    console.print()

    # Fancy header
    migration_header = Panel(
        Text.assemble(
            ("🚀 ", "bright_yellow"),
            ("Streaming Migration Mode", "bold bright_white"),
            ("\n\n", ""),
            ("┌─ ", "dim white"),
            ("Export", "bold cyan"),
            (" → ", "dim white"),
            ("Import", "bold green"),
            (" per dataset\n", "dim white"),
            ("├─ ", "dim white"),
            ("⚡ Real-time feedback and progress\n", "bright_blue"),
            ("├─ ", "dim white"),
            ("💾 Memory efficient processing\n", "bright_magenta"),
            ("└─ ", "dim white"),
            ("🔍 Automatic duplicate prevention", "bright_yellow"),
        ),
        border_style="bright_magenta",
        box=box.DOUBLE,
        padding=(1, 2),
    )
    console.print(migration_header)
    console.print()

    # Confirmation
    skip_existing = questionary.confirm(
        "Skip datasets that already exist in target?",
        default=True,
        style=custom_style
    ).ask()

    auto_create = questionary.confirm(
        "Auto-create knowledge bases in target?",
        default=True,
        style=custom_style
    ).ask()

    console.print()

    # Initialize migration
    migration = DifyMigration(source_configs, target_config)

    # Statistics
    success_count = 0
    skipped_count = 0
    failed_count = 0
    total_count = 0

    # Get existing datasets for tracking
    try:
        with console.status("[cyan]Checking existing datasets in target...", spinner="dots"):
            existing_datasets = migration.target_client.get_all_datasets()
            existing_names = {ds['name'] for ds in existing_datasets}

        console.print(f"📊 Found [yellow bold]{len(existing_names)}[/yellow bold] existing datasets in target\n")
    except Exception as e:
        console.print(Panel(
            f"[yellow]⚠️  Could not fetch existing datasets[/yellow]\n{str(e)}",
            border_style="yellow"
        ))
        existing_names = set()

    # Process each source
    for source_idx, source_client in enumerate(migration.source_clients, 1):
        console.print()

        # Source header with gradient
        source_header = Panel(
            Text.assemble(
                ("📦 ", "bright_cyan"),
                (f"Processing Source {source_idx}", "bold bright_white"),
                (" of ", "dim white"),
                (f"{len(migration.source_clients)}", "bold bright_cyan"),
            ),
            border_style="bright_cyan",
            box=box.HEAVY,
        )
        console.print(source_header)
        console.print()

        try:
            # Get datasets from this source
            with console.status(
                f"[bright_cyan]⚡ Fetching datasets from source {source_idx}...",
                spinner="dots12"
            ):
                all_datasets = source_client.get_all_datasets()

            # Dataset count info
            info_text = Text()
            info_text.append("📚 Found ", style="dim white")
            info_text.append(f"{len(all_datasets)}", style="bold bright_cyan")
            info_text.append(" dataset(s) to process", style="dim white")
            console.print(info_text)
            console.print()

            # Process each dataset with streaming
            for dataset in all_datasets:
                total_count += 1
                dataset_name = dataset['name']

                # Dataset card with box drawing
                console.print(f"╭─ [dim white]#{total_count}[/dim white] [bold bright_white]{dataset_name}[/bold bright_white]")

                # Check if already exists
                if skip_existing and dataset_name in existing_names:
                    console.print(f"╰─ [yellow bold]⏭️  Already exists, skipping[/yellow bold]\n")
                    skipped_count += 1
                    continue

                try:
                    # Export phase
                    console.print(f"├─ [cyan bold]📤 Exporting...[/cyan bold]")
                    export_data = migration.export_dataset(dataset['id'], source_client)

                    # Import phase
                    console.print(f"├─ [blue bold]📥 Importing to target...[/blue bold]")
                    result = migration.import_dataset(export_data, skip_existing=False, auto_create=auto_create)

                    if result:
                        console.print(f"╰─ [green bold]✅ Migration complete![/green bold]\n")
                        success_count += 1
                        existing_names.add(dataset_name)
                    else:
                        console.print(f"╰─ [yellow bold]⏭️  Skipped (already exists)[/yellow bold]\n")
                        skipped_count += 1

                except Exception as e:
                    error_msg = str(e)[:60] + "..." if len(str(e)) > 60 else str(e)
                    console.print(f"╰─ [red bold]❌ Failed: {error_msg}[/red bold]\n")
                    failed_count += 1

        except Exception as e:
            error_panel = Panel(
                Text.assemble(
                    ("❌ ", "bold red"),
                    (f"Failed to access Source {source_idx}", "bold red"),
                    ("\n\n", ""),
                    (str(e), "red"),
                ),
                border_style="red",
                box=box.HEAVY
            )
            console.print(error_panel)
            console.print()

    # Beautiful summary with enhanced visuals
    console.print()

    # Calculate success rate
    success_rate = (success_count / total_count * 100) if total_count > 0 else 0

    # Create summary panel with gradient
    summary_content = Table.grid(padding=(0, 2))
    summary_content.add_column(style="bold bright_white", justify="left")
    summary_content.add_column(style="bold", justify="right")

    summary_content.add_row("📊 Total Processed:", f"[cyan bold]{total_count}[/cyan bold]")
    summary_content.add_row("✅ Successful:", f"[green bold]{success_count}[/green bold]")
    summary_content.add_row("⏭️  Skipped:", f"[yellow bold]{skipped_count}[/yellow bold]")
    summary_content.add_row("❌ Failed:", f"[red bold]{failed_count}[/red bold]")
    summary_content.add_row()
    summary_content.add_row("📈 Success Rate:", f"[bright_magenta bold]{success_rate:.1f}%[/bright_magenta bold]")

    # Determine status color
    if failed_count == 0 and success_count > 0:
        status_color = "green"
        status_icon = "✅"
        status_text = "All migrations completed successfully!"
    elif failed_count > 0 and success_count > 0:
        status_color = "yellow"
        status_icon = "⚠️"
        status_text = "Migration completed with some failures"
    elif failed_count > 0:
        status_color = "red"
        status_icon = "❌"
        status_text = "Migration encountered errors"
    else:
        status_color = "cyan"
        status_icon = "ℹ️"
        status_text = "No datasets migrated"

    summary_panel = Panel(
        summary_content,
        title=f"[bold bright_white]🎉 Migration Complete 🎉[/bold bright_white]",
        subtitle=f"[{status_color}]{status_icon} {status_text}[/{status_color}]",
        border_style="bright_magenta",
        box=box.DOUBLE_EDGE,
        padding=(1, 2),
    )

    console.print(summary_panel)
    console.print()


def export_only(source_configs: List[DifyConfig]):
    """Export datasets only (backup) with beautiful display"""
    console.print()
    console.print(Panel(
        "[bold bright_yellow]💾 Export Only (Backup Mode)[/bold bright_yellow]\n\n"
        "Exporting all datasets to local JSON files...",
        border_style="yellow"
    ))
    console.print()

    # Dummy target for export-only
    target_config = DifyConfig(base_url="", api_key="")
    migration = DifyMigration(source_configs, target_config)

    exported_data = migration.export_all_datasets()

    console.print(f"\n✅ Exported [green bold]{len(exported_data)}[/green bold] datasets to [cyan]export_data/[/cyan]\n")

    # Show summary
    table = Table(
        title="📦 Exported Datasets",
        title_style="bold bright_yellow",
        box=box.ROUNDED,
        border_style="yellow"
    )
    table.add_column("Dataset Name", style="bright_white")
    table.add_column("📄 Documents", justify="right", style="bright_blue")
    table.add_column("📝 Segments", justify="right", style="bright_magenta")

    for data in exported_data:
        dataset = data['dataset']
        documents = data['documents']
        total_segments = sum(len(doc.get('segments', [])) for doc in documents)

        table.add_row(
            dataset['name'],
            str(len(documents)),
            str(total_segments)
        )

    console.print(table)
    console.print()


def import_from_backup(target_config: DifyConfig):
    """Import from backup files"""
    console.print()
    console.print(Panel(
        "[bold bright_blue]📂 Import from Backup[/bold bright_blue]\n\n"
        "Restoring datasets from exported JSON files...",
        border_style="blue"
    ))
    console.print()

    export_dir = Path('export_data')

    if not export_dir.exists():
        console.print(Panel(
            "[bold red]❌ export_data/ directory not found![/bold red]\n\n"
            "Please run [cyan]Export Only[/cyan] first.",
            border_style="red"
        ))
        return

    export_files = list(export_dir.glob('dataset_*.json'))

    if not export_files:
        console.print(Panel(
            "[bold red]❌ No backup files found in export_data/[/bold red]",
            border_style="red"
        ))
        return

    console.print(f"Found [green bold]{len(export_files)}[/green bold] backup files\n")

    skip_existing = questionary.confirm(
        "Skip datasets that already exist in target?",
        default=True,
        style=custom_style
    ).ask()

    # Dummy source for import-only
    source_configs = [DifyConfig(base_url="", api_key="")]
    migration = DifyMigration(source_configs, target_config)

    success_count = 0
    skipped_count = 0
    failed_count = 0

    console.print()

    with Progress(
        SpinnerColumn(spinner_name="dots"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Importing...", total=len(export_files))

        for export_file in export_files:
            progress.update(task, description=f"[cyan]Importing: {export_file.name}...")

            try:
                result = migration.import_from_file(str(export_file), skip_existing)
                if result is None:
                    skipped_count += 1
                else:
                    success_count += 1
            except Exception as e:
                failed_count += 1
                console.print(f"  [red]❌ {export_file.name}: {str(e)}[/red]")

            progress.advance(task)

    # Summary
    console.print()
    summary_table = Table(
        title="📊 Import Summary",
        title_style="bold bright_white",
        box=box.DOUBLE_EDGE,
        border_style="blue"
    )
    summary_table.add_column("Metric", style="bold bright_white", width=20)
    summary_table.add_column("Count", justify="right", style="bold", width=15)

    summary_table.add_row("Total Files", str(len(export_files)))
    summary_table.add_row("✅ Success", f"[green bold]{success_count}[/green bold]")
    summary_table.add_row("⏭️  Skipped", f"[yellow bold]{skipped_count}[/yellow bold]")
    summary_table.add_row("❌ Failed", f"[red bold]{failed_count}[/red bold]")

    console.print(summary_table)
    console.print()


def main_menu():
    """Main interactive menu with beautiful design"""
    print_banner()

    # Load configuration
    source_configs, target_config = load_configuration()

    # Show configuration
    show_sources_info(source_configs, target_config)

    while True:
        console.print()
        choice = questionary.select(
            "What would you like to do?",
            choices=[
                "🚀 Run Streaming Migration (Export→Import per dataset)",
                "📋 List All Knowledge Bases",
                "💾 Export Only (Backup)",
                "📂 Import from Backup",
                "🔧 Reconfigure",
                "❌ Exit"
            ],
            style=custom_style
        ).ask()

        if choice == "🚀 Run Streaming Migration (Export→Import per dataset)":
            run_migration(source_configs, target_config)

        elif choice == "📋 List All Knowledge Bases":
            list_all_datasets(source_configs, target_config)

        elif choice == "💾 Export Only (Backup)":
            export_only(source_configs)

        elif choice == "📂 Import from Backup":
            import_from_backup(target_config)

        elif choice == "🔧 Reconfigure":
            source_configs, target_config = interactive_config_setup()
            show_sources_info(source_configs, target_config)

        elif choice == "❌ Exit":
            console.print()
            console.print(Panel(
                "[bold bright_cyan]👋 Thank you for using Dify Migration Tool![/bold bright_cyan]\n\n"
                "✨ Migration made easy ✨",
                border_style="cyan",
                title="Goodbye"
            ))
            console.print()
            sys.exit(0)

        # Ask to continue
        console.print()
        if not questionary.confirm(
            "Continue?",
            default=True,
            style=custom_style
        ).ask():
            console.print()
            console.print(Panel(
                "[bold bright_cyan]👋 Thank you for using Dify Migration Tool![/bold bright_cyan]",
                border_style="cyan"
            ))
            console.print()
            sys.exit(0)


if __name__ == '__main__':
    try:
        main_menu()
    except KeyboardInterrupt:
        console.print("\n")
        console.print(Panel(
            "[bold yellow]⚠️  Interrupted by user[/bold yellow]\n\n"
            "Migration was stopped safely.",
            border_style="yellow",
            title="Interrupted"
        ))
        console.print("\n[bold cyan]👋 Goodbye![/bold cyan]\n")
        sys.exit(0)
    except Exception as e:
        console.print("\n")
        console.print(Panel(
            f"[bold red]❌ Unexpected Error[/bold red]\n\n"
            f"{str(e)}",
            border_style="red",
            title="Error"
        ))
        console.print()
        sys.exit(1)
