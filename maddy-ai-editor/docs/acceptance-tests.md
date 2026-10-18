# Acceptance gates and prioritized backlog

## Phase 0

- [x] Read both supplied briefs and inspect parent CEP project.
- [x] Inspect Windows tools and Premiere binary version.
- [x] Verify official UXP project/sequence and manifest documentation.
- [x] Define architecture, threat model, dependency lock and capability boundaries.

## Phase 1 and 2

- [x] GUI launches, remains responsive, and is visually reviewed on Windows.
- [x] Import video, show metadata/progress/activity, persist settings, cancel work.
- [x] Generate fixture; prove duration, silence ranges, scene extraction and source checksum.
- [x] Invalid media and missing tools produce visible actionable errors.
- [x] Validate edited ranges/JSON; retime Unicode captions; reject invalid rates for EDL.
- [ ] Review real English/Kannada speech accuracy and long-footage performance.
- [x] Expand single active job into persistent multi-job queue with interrupted-job recovery.
- [x] Add integrated source/output playback preview and first-run onboarding wizard.

## Phase 3 and 4

- [ ] Load plugin through Adobe UXP Developer Tool and inspect a disposable project in 26.5.2.
- [ ] Record host version, missing-project state, disconnect and timeout behavior.
- [ ] Verify manifest permissions and actual Origin behavior.
- [ ] Test documented sequence duplication and edit actions in a disposable project.
- [ ] Add operation approval dialog, original project backup, idempotent journal, undo/recovery tests.
- [ ] Keep writes/export disabled until these gates pass.

## Phase 5

- [x] SDK handshake and all thirteen named tools expose strict schemas.
- [x] Reject unauthorized paths, malformed plans, unapproved/mismatched/expired/reused tokens.
- [x] No MCP arbitrary-shell or approval-issuance tool.

## Phase 6 and 7

- [x] Build Windows one-folder executable; run frozen smoke test.
- [x] Build Inno installer, generate SHA256 and dependency/license inventory.
- [x] Test isolated local install, installed video analysis, uninstall and registry cleanup.
- [ ] Package CCX in Adobe UXP Developer Tool using registered production plugin ID.
- [ ] Test offline/online install, update and uninstall on clean Windows 11 VM.
- [ ] Scan artifacts, review third-party obligations, obtain release sign-off.

Priority is working local analysis, then real UXP inspection, then safe edits,
then release validation. The final product is not complete until all release gates pass.
