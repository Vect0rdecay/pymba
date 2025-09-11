# Pymba Development Guide

## Project Status

Pymba is currently in early development. The core orchestration framework and P-modules (Pre-checking/Extraction) are implemented as a proof of concept.

## Current Implementation

### Completed Components

1. **Core Framework**
   - Configuration management system
   - Module loading and execution framework
   - Comprehensive logging system
   - CLI interface

2. **P-Modules (Pre-checking/Extraction)**
   - `P02_firmware_bin_file_check`: Basic firmware file analysis
   - `P50_binwalk_extractor`: Binwalk-based firmware extraction
   - `P55_unblob_extractor`: Unblob-based extraction (placeholder)
   - `P60_deep_extractor`: Deep extraction for nested archives (placeholder)
   - `P99_prepare_analyzer`: Final preparation for analysis

3. **Helper Functions**
   - File system utilities
   - System utilities
   - Basic extraction utilities

## Testing

Run the test script to verify the current implementation:

```bash
cd /home/admin/pymba
python test_pymba.py
```

This will:
- Create a test firmware structure
- Run the P-modules on it
- Demonstrate the analysis pipeline
- Generate logs and reports

## Architecture

Pymba follows the same modular architecture as EMBA:

- **P-Modules**: Pre-checking and firmware extraction
- **S-Modules**: Security analysis (planned)
- **L-Modules**: Live emulation (planned)
- **F-Modules**: Final reporting (planned)
- **Q-Modules**: AI-powered analysis (planned)
- **D-Modules**: Differential analysis (planned)

## Next Steps

1. **Complete P-Modules**: Implement remaining extraction modules
2. **S-Modules**: Port security analysis modules
3. **Helper Functions**: Complete utility functions
4. **Testing**: Add comprehensive test suite
5. **Documentation**: Complete API documentation

## Dependencies

See `requirements.txt` for Python dependencies. External tools required:
- binwalk (for P50 module)
- unblob (for P55 module)
- Various security analysis tools (for S-modules)

## Development Notes

- The framework is designed to be compatible with EMBA's module structure
- Modules can be written as classes (inheriting from BaseModule) or functions
- Configuration supports both YAML and EMBA-style profiles
- Threading is supported with automatic thread management
- Logging provides both file and console output with rich formatting

