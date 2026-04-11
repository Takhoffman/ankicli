# Distribution And Installer Contract

Use this reference when the task is about packaging, artifact naming, installer scripts, site install commands, or standalone release validation.

This repository has two names that must stay aligned:

- PyPI distribution: `anki-agent-toolkit`
- executable command: `ankicli`

## Distribution surfaces

- GitHub Releases standalone artifacts
- raw installer entrypoints:
  - [`scripts/install.sh`](/Users/thoffman/ankicli/scripts/install.sh)
  - [`scripts/install.ps1`](/Users/thoffman/ankicli/scripts/install.ps1)
- product site install commands
- optional PyPI package distribution

## Artifact contract

Expected release asset names:

- `ankicli-<version>-darwin-arm64.tar.gz`
- `ankicli-<version>-darwin-x64.tar.gz`
- `ankicli-<version>-linux-x64.tar.gz`
- `ankicli-<version>-windows-x64.zip`
- `ankicli-<version>-checksums.txt`

Supported release targets:

- `darwin-x64`
- `darwin-arm64`
- `linux-x64`
- `windows-x64`

## Installer contract

Verify these together:

- raw installer URLs still exist
- expected asset names still match the release workflow
- checksums still match the installer lookup contract
- install location and PATH messaging are still accurate
- post-install verification commands still work

Relevant code:

- [`src/ankicli/app/releases.py`](/Users/thoffman/ankicli/src/ankicli/app/releases.py)
- [`scripts/install.sh`](/Users/thoffman/ankicli/scripts/install.sh)
- [`scripts/install.ps1`](/Users/thoffman/ankicli/scripts/install.ps1)

## Site and docs checks

If site or install docs changed, validate:

```bash
cd site
npm install
npm run build
```

Confirm:

- homepage install commands match the current installers
- docs describe the supported install path
- package name, command name, version, and release wording are consistent

## Release blockers

Treat these as release-blocking:

- artifact name drift
- checksum mismatch
- installer script points at missing assets
- standalone artifact launches but `ankicli --json doctor backend` fails
- site install commands drift from the real installer contract
- package version, git tag, and asset version drift
