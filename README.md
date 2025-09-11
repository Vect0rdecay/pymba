# Pymba - Python Firmware Security Analyzer

A Python port of the EMBA (Embedded Linux Analyzer) firmware security analysis tool.

## Overview

Pymba is designed as a comprehensive firmware security analysis framework that provides:
- Automated firmware extraction and analysis
- Static and dynamic security analysis
- SBOM (Software Bill of Materials) generation
- Vulnerability detection and reporting
- Web-based reporting interface

## Architecture

Pymba follows a modular architecture with the following phases:

- **P-Modules**: Pre-checking and firmware extraction
- **S-Modules**: Security analysis and vulnerability detection
- **L-Modules**: Live emulation and dynamic analysis
- **F-Modules**: Final reporting and SBOM generation
- **Q-Modules**: AI-powered analysis (Quest modules)
- **D-Modules**: Differential analysis between firmware versions

## Installation

```bash
git clone <repository-url>
cd pymba
pip install -r requirements.txt
```

## Usage

```bash
python -m pymba --firmware /path/to/firmware --log-dir /path/to/logs
```

## Development Status

Currently implementing:
- Core orchestration framework
- P-Modules (Pre-checking/Extraction)

## License

GPL-3.0 (same as original EMBA)

# pymba
