# Test fixtures

**Synthetic until hardware day.** Shapes follow OpenBambuAPI (mqtt.md) and the OctoPrint
REST docs. On the farm PC, replace them with real recordings (Phase 2 runbook step 7):
`h2s_report_full.json` = first full `pushall` reply, `octoprint_*.json` = `GET /api/printer`
and `GET /api/job` during a print. `stat.door` is a placeholder path until Gate 1 Q2 is answered.
The `subtask_name` deliberately contains a control character and an injection attempt.
