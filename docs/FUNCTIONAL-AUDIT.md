# Functional audit — 24 October 2026

## Scope and results

Reviewed the active React workspace, API, role guards, persisted records, photo inputs, comments, submissions, independent review, audits, red tags, assets, reports and unused source graph. UI testing used explicitly synthetic local-preview records. Production business records were not used for destructive tests.

| Area | Confirmed issue / change | Evidence |
|---|---|---|
| Start work | Empty JSON bodies with the browser's Content-Type header caused JSONDecodeError and HTTP 500. Access checks now handle empty bodies and return 422 for malformed JSON; the client omits JSON Content-Type when there is no body. | Reproduced through browser; regression test and browser retest pass. |
| Comments | One-line input, no attachments, no bounds/blank validation; comment history could lag behind posted content. Added multiline text, optional photo, refreshed persisted detail/history, whitespace-preserving display, 5,000-character bound and authenticated author. | Browser post + reload, loaded photo check, API tests. |
| Internal notes | Internal comments were included in every scoped work response. They are now restricted to reviewers and cannot be posted by non-reviewers. | Negative API tests. |
| Uploads | Browser-only type/size checks accepted fake image data at the server. New embedded raster uploads are decoded and validated, with actual MIME matching, full image verification, 3 MB/20 MP limits and no animation. Metadata is derived from the actual image. | Valid PNG/JPEG/WebP, mismatched MIME, corrupt data, remote URLs, SVG and over-limit test cases. |
| Photo controls | Added gallery/file chooser, separate camera capture, reading state, preview and removal. Save/post buttons wait for image reading. | Browser invalid/oversize/valid selection and preview checks. Physical phone camera permissions remain a device test. |
| Evidence lifecycle | Existing review/completed records accepted new evidence. Evidence now locks under review and after completion; before images may also be supplied when submitting a report. | State-guard tests; browser before/after submission and independent completion. |
| Assignment | Read-only users could be assigned executable work; leaders could be assigned another zone and then be unable to see their task. Choices and server validation now enforce executable role and assigned zone. | Positive browser assignment, negative API tests. |
| Independent review | Assignment checks alone allowed a supervisor to review an unassigned report they submitted. The actual recorded submitter is now also blocked; the UI follows that rule. PostgreSQL transitions lock and refresh the record to serialize competing state changes. | Negative submitter approval/rejection tests and successful independent review. PostgreSQL concurrency still needs a dedicated load test. |
| Audit records | Notes were saved but not available in a detail view; evidence had no upload field. Added assessment detail view, timestamp, optional photo and persisted photo records. | Browser save + reload with a valid zero score, notes and loaded image; API persistence tests. |
| Red tags | Saved photos/notes were inaccessible; API allowed invalid quantities, blank decisions, closing holds and changing closed records. Added detail/photos, prefilled disposition notes, disabled closure for holds, schema/state guards. | Browser photo/details, hold then executed closure; API negative tests. |
| Outcomes | Report outcome was collected but not displayed in the work details. It is now visible and multiline text retains line breaks. | Browser review screen. |
| Dates | Naive UTC API timestamps were interpreted as local time. Shared parsing now preserves UTC timestamps, explicit offsets and calendar dates. | Three Node tests. |
| PDF | Old branding, interpreted markup, assumed safety/sign-off language, and counts instead of photos. User text is escaped, recorded facts are used, and bounded before/after images are embedded without remote fetching. | API export, rendered page review, markup regression test. |
| Public health | HEAD / returned 405. GET/HEAD now work; health probes check DB connectivity and expose the deployed revision for troubleshooting. | Isolated public-endpoint tests. |
| Dead code | 30 unreachable legacy source/assets, 10 unused API helpers, mock screens, and two unused direct dependencies were removed. Database models/tables were preserved. Former Austin-fixture tests were replaced with isolated current API tests. | Import graph, complete frontend build/typecheck/lint. |

## Upload and comment fields

- Work creation: optional before photo.
- Report submission: optional before photo, required after photo and corrective action; outcome text is displayed.
- Work discussion: multiline comment plus optional photo. Text is required; file-only comments are not supported.
- Assessments: notes and optional assessment photo; click a zone's assessment to read stored notes and view evidence.
- Red tags: reason and optional item photo; click the item to view evidence and disposition notes. Authorized reviewers record the disposition.

These fields accept images, not arbitrary PDF/Office documents. The UI currently exposes one photo per input; comment/audit APIs allow up to three photos for future multiple-file UI work.

## Validation

- 20 isolated backend integration/public API tests and three Node date tests.
- Production web build, TypeScript and lint.
- Browser checks for comment/photo persistence, upload errors, start/report/approval, assessment notes/photo and zero score, red-tag photo/hold/closure.
- Phone-width layout checks and generated PDF visual inspection.

## Remaining improvements / limitations

1. **Asset-code uniqueness:** codes are currently globally unique, including across plants. Changing this to per-plant uniqueness needs a reviewed migration of the existing database constraint. It was not silently altered during this audit.
2. **Media scale:** evidence remains embedded in PostgreSQL. Private object storage, thumbnails, quotas and paginated media loading are needed for larger deployments.
3. **Accounts:** normal-user enrollment, password recovery, MFA/SSO and test-account renewal/revocation remain release work. Existing six testing accounts retain their prior expiry and passwords.
4. **Documents:** controlled SOP/PDF document uploads, versioning and question-level audit checklists remain product work; image inputs do not imply these features exist.
5. **Verification limits:** physical Android/iPhone camera/keyboard tests, accessibility audit, PostgreSQL contention/load tests and large-dataset pagination tests remain. A passing browser viewport check is not universal-device certification.
6. Older external or invalid photo records remain readable; validation applies to newly uploaded evidence. The PDF safely reports an unavailable image instead of fetching untrusted remote URLs.
