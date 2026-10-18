# Threat model

| Threat | Control | Remaining work |
|---|---|---|
| Unauthenticated localhost clients | Random session bearer token; loopback only | OS user boundary is trusted; tokens must stay private |
| Browser cross-origin calls/DNS rebinding | Host and Origin checks, no CORS, request size limit | Verify actual UXP origin behavior without broadening access |
| Agent reads arbitrary files | Canonical strict path allowlist, resolve symlinks | Race-resistant file handles for adversarial multi-user file replacement |
| Agent modifies project without consent | No approval issuance tool, payload-bound single-use expiring tokens; writes disabled | Wire actual approval dialog only after timeline adapter QA |
| Command injection | Fixed argument arrays, shell=False, no arbitrary shell tool | Configured executables are user-trusted |
| Malicious media URL/network access | Local files and FFmpeg file/pipe protocol whitelist | Sandboxed decoding and larger fuzz corpus before public release |
| Hung processes/large logs | Timeouts, cancellation, bounded read/disk output | Long-footage soak and resource quotas on clean VM |
| Source loss | Analysis does not write source; saves reject source overwrite | Project backup and duplicate recovery gate before any edit |
| Data leakage | No uploads; no cloud adapter enabled; no embedded keys | Support-bundle redaction and credential vault when cloud is implemented |
| False connection state | Heartbeats expire; no stale project information returned | Host disconnect and version-mismatch real-Premiere QA |

The bridge is not a security boundary against malware already running as the
same Windows account. Do not distribute a release until dependencies, licenses,
antivirus and clean-machine installation have been reviewed.
