# Dify Migration Tool

Tool Python untuk migrasi **knowledge bases** dan **workflows/apps** dari satu instance Dify ke instance Dify lainnya, termasuk semua documents, chunks/segments, metadata, dan DSL workflows.

## Overview

Tool ini memungkinkan Anda untuk:
- Export knowledge bases dari Dify source instance
- Import knowledge bases ke Dify target instance
- **Export dan import workflows/apps (DSL)**
- **Complete migration (KB + Workflows)**
- Migrasi dari satu atau **multiple sources** ke target
- Backup knowledge bases dan workflows ke file

## Features

### Core Features
- ✅ **Multiple source support** - Migrate dari multiple Dify API keys sekaligus
- ✅ **Workflow/App migration** - Migrate DSL workflows dan apps
- ✅ **Complete migration** - Migrate KB + Workflows dalam satu operasi
- ✅ **Parallel execution** - KB dan Workflows migrate bersamaan (2x faster!)
- ✅ **Auto-create knowledge bases** - Otomatis create knowledge base di target
- ✅ Export single atau multiple knowledge bases
- ✅ Import dari file JSON/YAML atau langsung dari source
- ✅ Preserve document structure dan segments
- ✅ Preserve workflow configurations dan dependencies
- ✅ Skip items yang sudah ada (configurable)
- ✅ Logging lengkap untuk tracking progress
- ✅ Error handling yang robust
- ✅ Support untuk pagination pada large datasets

### 🎨 CLI GUI Features
- ✅ **Beautiful terminal UI** - Colors, borders, formatted tables
- ✅ **Interactive menus** - Easy navigation with arrow keys
- ✅ **Progress bars & spinners** - Real-time progress tracking
- ✅ **Auto configuration** - Interactive setup wizard
- ✅ **Live feedback** - See migration status in real-time
- ✅ **User-friendly** - Perfect untuk first-time users

## Prerequisites

- Python 3.7 atau lebih tinggi
- Dify API key untuk source instance(s)
- Dify API key untuk target instance
- Akses network ke Dify instances

## Installation

### Quick Setup (Recommended)

```bash
# Clone atau download repository ini
cd migrate-dify-knowledge

# Run setup script
./setup.sh

# Edit .env dengan API keys Anda
nano .env

# Done! Run CLI GUI
python cli_gui.py
```

### Manual Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Copy dan edit konfigurasi
cp .env.example .env
nano .env
```

## Configuration

### .env File (Recommended)

**Knowledge Bases Only:**
```bash
SOURCE_BASE_URL=https://api.dify.ai
SOURCE_API_KEYS=dataset-key1,dataset-key2
TARGET_BASE_URL=https://api.dify.ai
TARGET_API_KEY=dataset-yyyyy
```

**With Workflow Migration:**
```bash
# Knowledge Base API Keys
SOURCE_BASE_URL=https://api.dify.ai
SOURCE_API_KEYS=dataset-key1,dataset-key2
TARGET_BASE_URL=https://api.dify.ai
TARGET_API_KEY=dataset-yyyyy

# Console API Credentials (for workflow migration)
SOURCE_EMAIL=your-source-email@example.com
SOURCE_PASSWORD=your-source-password
TARGET_EMAIL=your-target-email@example.com
TARGET_PASSWORD=your-target-password
```

### Getting API Keys

1. Login ke Dify instance Anda
2. Go to **Knowledge** → **API**
3. Copy API key (starts with `dataset-`)

**IMPORTANT:** Use **Knowledge Base API Key**, not Application API Key!

## Quick Start

### 🎨 Interactive CLI GUI (Recommended)

Cara paling mudah dengan beautiful interface:

```bash
python cli_gui.py
```

**Features:**
- Interactive menus with arrow key navigation
- Beautiful progress bars and spinners
- Auto configuration setup wizard
- Real-time feedback dan formatted tables
- User-friendly for beginners

### 🔧 Command Line Scripts

Untuk automation dan scripting:

```bash
# Full migration
python dify_migration.py

# List all datasets
python scripts/list_datasets.py

# Export only (backup)
python scripts/export_only.py

# Import from backup
python scripts/import_from_backup.py

# See demo (no API keys needed)
python scripts/demo.py
```

## Project Structure

```
migrate-dify-knowledge/
├── 🎨 Main Tools
│   ├── cli_gui.py              # Interactive CLI GUI (recommended)
│   └── dify_migration.py       # Core migration engine
│
├── 📁 Scripts
│   ├── list_datasets.py        # List all datasets
│   ├── export_only.py          # Export/backup only
│   ├── import_from_backup.py   # Import from files
│   └── demo.py                 # Demo without API keys
│
├── 📚 Documentation
│   ├── QUICK_REFERENCE.md      # Cheat sheet
│   ├── CLI_GUI_GUIDE.md        # CLI GUI guide
│   ├── SETUP.md                # Setup guide
│   ├── MULTIPLE_SOURCES_GUIDE.md # Multiple sources guide
│   ├── PROJECT_STRUCTURE.md    # Project structure
│   └── CHANGELOG.md            # Version history
│
├── ⚙️ Configuration
│   ├── .env.example            # Environment template
│   ├── requirements.txt        # Python dependencies
│   └── setup.sh                # Setup script
│
└── 📦 Generated (gitignored)
    ├── .env                    # Your configuration
    ├── export_data/            # Backup files
    └── *.log                   # Log files
```

## Usage Examples

### Example 1: Full Migration with CLI GUI

```bash
python cli_gui.py
```

Select: `🚀 Run Full Migration (Export + Import)`

The tool will:
1. Show your configuration
2. Ask for options (skip existing, auto-create)
3. Export from all sources
4. Import to target with progress bars
5. Show detailed summary

### Example 2: Multiple Sources Migration

Edit `.env`:
```bash
SOURCE_API_KEYS=dataset-workspace1,dataset-workspace2,dataset-workspace3
```

Run:
```bash
python cli_gui.py
```

The tool will migrate from all 3 workspaces to target automatically!

### Example 3: List All Datasets

```bash
python cli_gui.py
```

Select: `📋 List All Knowledge Bases`

Shows formatted tables with:
- All datasets from each source
- Document counts
- Word counts
- Target datasets

### Example 4: Export for Backup

```bash
python cli_gui.py
```

Select: `💾 Export Only (Backup)`

Exports all datasets to `export_data/` folder as JSON files.

### Example 5: List All Workflows/Apps

```bash
python scripts/list_apps.py
```

Shows all workflows and apps from source(s) and target with:
- App names
- Modes (workflow, chatbot, agent, etc.)
- Last updated timestamps

### Example 6: Migrate Workflows Only

```bash
python scripts/migrate_apps.py
```

Interactive prompts will ask:
- Skip existing apps?
- Include secret variables?
- Use streaming mode?

### Example 7: Complete Migration (KB + Workflows)

```bash
python cli_gui.py
```

Select: `🌟 Complete Migration (KB + Workflows)`

Or via command line:
```bash
python scripts/complete_migration.py
```

This migrates EVERYTHING:
1. All knowledge bases with documents
2. All workflows/apps with configurations

**By default runs in PARALLEL mode** - KB and Workflows migrate simultaneously for maximum speed! 🚀

### Example 8: Command Line (for Scripts)

```bash
# Full migration (non-interactive)
python dify_migration.py                 # KB only

# Workflow migration
python scripts/migrate_apps.py           # Workflows only
python scripts/complete_migration.py     # KB + Workflows

# List operations
python scripts/list_datasets.py          # List KB
python scripts/list_apps.py              # List workflows

# Export operations
python scripts/export_only.py            # Export KB
python scripts/export_apps.py            # Export workflows
```

## Multiple Sources

Tool supports migrating from **multiple Dify API keys** at once:

**Use Cases:**
- Consolidate multiple workspaces into one
- Merge team knowledge bases
- Migration from multiple instances

**How it works:**
1. Provide multiple API keys (comma-separated in .env)
2. Tool fetches datasets from all sources
3. Auto-creates knowledge bases in target
4. Migrates all documents and segments

See [docs/MULTIPLE_SOURCES_GUIDE.md](docs/MULTIPLE_SOURCES_GUIDE.md) for detailed guide.

## CLI GUI

Beautiful interactive terminal interface with:
- 🎨 Colorful ASCII art banner
- 📊 Formatted tables with borders
- ⚡ Animated progress bars & spinners
- 🎯 Interactive menus
- ✅ Real-time feedback
- 🔧 Auto configuration wizard

See [docs/CLI_GUI_GUIDE.md](docs/CLI_GUI_GUIDE.md) for detailed guide.

## Documentation

- **[docs/QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md)** - Quick reference card (cheat sheet)
- **[docs/CLI_GUI_GUIDE.md](docs/CLI_GUI_GUIDE.md)** - Complete CLI GUI guide
- **[docs/SETUP.md](docs/SETUP.md)** - Quick setup guide
- **[docs/MULTIPLE_SOURCES_GUIDE.md](docs/MULTIPLE_SOURCES_GUIDE.md)** - Multiple sources guide
- **[docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md)** - Project structure details
- **[docs/CHANGELOG.md](docs/CHANGELOG.md)** - Version history

## Troubleshooting

### "No configuration found"
```bash
cp .env.example .env
nano .env
```

### "401 Unauthorized"
- Check API key is valid
- Use Knowledge Base API key (starts with `dataset-`)

### "404 Not Found"
- Check base URL is correct
- Cloud: `https://api.dify.ai`
- Self-hosted: `https://your-domain.com/api`

### Colors not showing (CLI GUI)
- Use modern terminal (Windows Terminal, iTerm2, etc.)
- Update terminal for Unicode support

### More Issues
- Check logs: `tail -f dify_migration.log`
- See troubleshooting in documentation
- Run demo: `python scripts/demo.py`

## CLI GUI vs Command Line

| Feature | CLI GUI | Command Line |
|---------|---------|--------------|
| Interactive | ✅ Yes | ❌ No |
| Beautiful UI | ✅ Yes | ⚠️  Basic |
| Progress bars | ✅ Animated | ⚠️  Text only |
| Configuration | ✅ Interactive | ⚠️  Manual |
| Menus | ✅ Yes | ❌ No |
| Colors | ✅ Yes | ⚠️  Limited |
| Automation | ❌ No | ✅ Yes |
| Scripting | ❌ No | ✅ Yes |
| Background | ❌ No | ✅ Yes |

**Use CLI GUI when:**
- First time user
- Want visual feedback
- Interactive operations
- Learning the tool

**Use Command Line when:**
- Automation/scripting
- CI/CD pipelines
- Cron jobs
- Background operations

## Features Timeline

- **v1.0** - Basic migration, single source
- **v2.0** - Multiple sources, auto-create KB
- **v2.1** - Interactive CLI GUI 🎨
- **v3.0** - Workflow/App migration 🔄

## License

MIT License - Free for personal and commercial use

## Support

For issues or questions:
1. Check documentation in `docs/` folder
2. Review log file: `dify_migration.log`
3. Run demo: `python scripts/demo.py`
4. See examples in this README

## Quick Command Reference

```bash
# Setup
./setup.sh                           # Auto setup
cp .env.example .env                 # Manual setup

# Main tools
python cli_gui.py                    # Interactive CLI (recommended)
python dify_migration.py             # Command line migration (KB only)

# Knowledge Base scripts
python scripts/list_datasets.py      # List all datasets
python scripts/export_only.py        # Export/backup KB
python scripts/import_from_backup.py # Import KB from files

# Workflow/App scripts
python scripts/list_apps.py          # List all workflows/apps
python scripts/export_apps.py        # Export/backup workflows
python scripts/migrate_apps.py       # Migrate workflows only
python scripts/complete_migration.py # Migrate KB + Workflows

# Logs
tail -f dify_migration.log           # Monitor logs
```

---

**Version:** 3.0.0
**Updated:** 2025-11-10
**Author:** Dify Migration Tool Team
**Repository:** migrate-dify-knowledge

## What's New in v3.0

### 🎉 Workflow/App Migration Support
- **Export/Import DSL workflows** - Migrate complete workflow configurations
- **Console API integration** - Authenticate with email/password for workflow operations
- **Preserve dependencies** - Maintain tool configurations and connections
- **Secret handling** - Optional inclusion of environment variables

### ⚡ Parallel Execution
- **PARALLEL mode by default** - KB and Workflows migrate simultaneously
- **2x faster** - Both migrations run in separate threads
- **Configurable** - Choose between parallel or sequential mode
- **Error isolation** - Individual error handling for each thread

### ✨ Enhanced CLI GUI
- **Workflow menu options** - New interactive menus for workflow operations
- **Complete migration** - Single-click KB + Workflow migration
- **Parallel execution toggle** - Choose parallel vs sequential
- **Status indicators** - Visual feedback for workflow migration availability
- **Smart menus** - Context-aware options based on credentials

### 📜 New Scripts
- `scripts/list_apps.py` - List all workflows and apps
- `scripts/export_apps.py` - Export workflows to YAML files
- `scripts/migrate_apps.py` - Migrate workflows only
- `scripts/complete_migration.py` - Complete KB + Workflow migration
