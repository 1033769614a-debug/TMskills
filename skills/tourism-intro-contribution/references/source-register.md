# Source register

Status: `VERIFIED`

This status verifies the internal lecture-derived method against the user-supplied recording. It does **not** verify that the panelists' advice is formal policy of *Tourism Management*.

## Source identity

- Source ID: `SRC-LECTURE-001`
- User-described title: 《如何写出有说服力的引言与研究贡献？》
- User-described context: *Tourism Management* online seminar, October 2026
- Source type: complete screen recording exported from the user's macOS Photos library
- Recording metadata date: 5 October 2026
- Original duration: 3,688.822 seconds
- Verified lecture-content boundary: 0–3,589 seconds (00:00:00–00:59:49)
- Original video: HEVC, 2,622 × 1,206, 6,797,498,832 bytes
- Original SHA-256: `bd17a774c2bebe6fe2b677f77145b3bb5ba88904be8923b1f6efa6d5159f8a1e`
- Public event-recap verification: completed on 14 October 2026
- Speaker names and participant identities: retained only in ignored private working files

## Public corroborating source

- Source ID: `SRC-PUBLIC-001`
- Page title: `TM2026年10月网络研讨会内容回顾`
- Displayed account name: `Tourism Management 旅游管理`
- Page date: 5 October 2026
- Recap URL: <https://mp.weixin.qq.com/s/qz7x-5TDqkohwK_oSN7dJg>
- Public replay URL resolved from the recap: <https://www.bilibili.com/video/BV1d8p56tENQ/>
- Coverage: a concise recap organized around fifteen audience questions about problem importance, gap logic, contribution credibility, context, theory use, introduction structure, and responsible AI assistance

The public recap corroborates the event identity and the main themes independently extracted from the user's recording. It does not replace the timestamped recording anchors, and the account display name alone is not evidence that every statement is formal publisher or journal policy. See [public-event-recap.md](public-event-recap.md) for the bounded public-source mapping.

## Ingestion and verification record

- Audio: 16 kHz mono PCM WAV, 3,688.883 seconds; audio/video duration difference is approximately 0.06 seconds.
- ASR: OpenAI Whisper `base`, English, segment timestamps, Apple MPS; 571 raw segments.
- Content-normalized transcript: 566 segments through 00:59:49; five post-event hallucinated segments were excluded by an explicit recorded boundary.
- Uncertainty log: 96 normalized segments are marked uncertain from ASR probability thresholds and remain timestamp-addressable.
- On-screen-caption verification: 1,197 three-second caption samples processed with macOS Vision OCR; 1,196 contained readable text.
- Speaker separation: 61 continuous turns across three panel roles, one moderator role, and an anonymized audience-participant label; each transcript segment records whether attribution came from a caption name, active-view label, or carry-forward evidence.
- Visual record: 74 change-detection candidates retained. A clear slide at approximately 00:09:20 visually corroborates the introduction's early interpretive role, the importance-versus-rigor distinction, and contribution positioning.
- Slide limitation: the presenter stopped screen sharing after technical difficulty. Other slide thumbnails were visible but were not presented clearly; the method does not infer their hidden content.
- Q&A: present and included; the method reference labels preferences and Q&A advice rather than converting them into universal rules.

## Verification decision

The lecture source gate is satisfied because:

1. the complete recording was ingested and cryptographically identified;
2. speaker turns were separated using the recording's own visual caption evidence;
3. available slide evidence was captured and unavailable slide content was explicitly bounded;
4. uncertain ASR is preserved with timestamps for rechecking;
5. every substantive rule in `lecture-method.md` has transcript or visual anchors;
6. a public event recap independently corroborates the event identity and principal themes;
7. the private/public reuse boundary is recorded below.

## Authority boundary

- Treat the material as panel guidance and editorial judgment.
- Do not describe it as an official submission requirement, journal policy, or guarantee of acceptance.
- Verify current publisher and journal requirements independently when a task depends on them.
- Do not quote an uncertain segment without replaying the corresponding recording span or checking the on-screen caption OCR.
- Use the public recap as corroboration and a reader-accessible source, not as proof of a mandatory submission rule.

## Publication boundary

Reuse authorization for the raw event content has not been confirmed. Therefore the default GitHub release must exclude:

- the raw or proxy recording and extracted audio;
- the full or reconstructed transcript and OCR corpus;
- slide and participant-gallery images;
- speaker and participant identities;
- unpublished manuscript text supplied during later tests;
- local filesystem paths and private runtime artifacts.

The distributable skill may contain independently phrased workflow rules, newly written examples, compact provenance metadata, evaluation cases, and source timestamps/anchor ranges. Reassess this boundary only if the user supplies explicit reuse permission.

Public source links and brief original summaries may be distributed. Do not mirror the recap article, its images, or the linked replay inside the repository.
