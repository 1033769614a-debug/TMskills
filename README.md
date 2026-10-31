# TMskills

`TMskills` 是一个面向旅游与酒店管理研究的、来源可核查的 Codex 审稿辅助 Skill。它从 *Tourism Management* 公开网络研讨会中编辑与资深学者关于引言、研究问题和理论贡献的讨论里蒸馏审稿判断，用于辅助审查旅游管理类论文与手稿的引言、文献综述和研究贡献论证。

它重点检查：

- 引言是否提出了重要、非显然且值得回答的研究问题；
- 文献综述是否形成清晰的学术对话，而不是简单罗列文献；
- 所谓“研究空白”是否说明了尚未解决的理论张力、机制或边界条件；
- 旅游情境、文化背景或新技术是否真正改变既有解释；
- 研究发现、知识贡献和理论贡献是否被准确区分；
- 贡献主张是否与研究设计、证据和结论相匹配；
- 引言、文献综述、讨论与结论是否保持同一条核心论证线索。

The skill distils reviewer-facing reasoning from a public *Tourism Management* webinar to audit the introductions, literature reviews, and contribution arguments of tourism and hospitality manuscripts.

该方法来自用户提供的 2026 年 10 月网络研讨会录屏，并与[公开会议回顾](https://mp.weixin.qq.com/s/qz7x-5TDqkohwK_oSN7dJg)交叉核对；会议回顾还提供了[公开录播](https://www.bilibili.com/video/BV1d8p56tENQ/)。这些内容属于编辑与学者的公开写作和审稿建议，不是 *Tourism Management* 的正式投稿规则，也不能保证论文被送审或录用。

## Included skill

- `skills/tourism-intro-contribution/`
  - 审查研究问题的重要性、文献对话、研究空白与贡献可信度；
  - 检查引言和文献综述之间的逻辑衔接；
  - 区分新颖性、研究情境、研究发现、知识贡献和理论贡献；
  - 在修改前建立“主张—证据”对应表；
  - 不虚构发现、文献、机制、因果性或可推广性；
  - 可与文献检索、论文起草、语言润色和独立审稿 Skill 协同使用。

## Install locally

Copy `skills/tourism-intro-contribution` into the user's Codex skills directory, then restart or refresh Codex skill discovery. Keep the folder name unchanged so `$tourism-intro-contribution` remains stable.

## Typical use

```text
Use $tourism-intro-contribution to diagnose this introduction before rewriting it.
Build a claim-to-evidence map, identify the weakest gap and contribution claim,
then revise only what my study design and findings can support.
```

For an end-to-end paper workflow, use this skill first for argument architecture, then a literature/citation workflow, an academic drafting workflow, language polishing, and finally an independent reviewer pass. The integration contract is in `references/integration-contract.md`.

## Validation

The skill itself has no Python runtime dependency. The optional ingestion-tool tests require an existing Python environment with NumPy and OpenCV; the Skill Creator validator additionally requires PyYAML. The repository does not auto-install or auto-download these packages or a Whisper model.

From the repository root:

```bash
python3 tests/test_tools.py -v
python3 tools/release_guard.py .
python3 /path/to/skill-creator/scripts/quick_validate.py \
  skills/tourism-intro-contribution
```

The release guard rejects private media, transcripts, unpublished-paper filenames, absolute home paths, and an unverified source register.

## Privacy and copyright boundary

The public repository must not include the recording, proxy video, audio, full transcript, OCR corpus, slide images, participant identities, unpublished manuscripts, or local paths. Those materials belong only in ignored `private-source/` and `work/` directories.

The distributable skill contains independently phrased workflow rules, newly written examples, compact provenance information, and evaluation cases. Raw-source reuse permission has not been established.

## Runtime versus ingestion tools

The skill itself is Markdown and needs no media dependencies at use time. The optional source-ingestion tools support macOS media conversion, macOS Vision OCR, OpenCV frame extraction, and an isolated OpenAI Whisper runtime. See `SOURCE_INTAKE.md` for the private ingestion pipeline.

## License

The distributable repository files are released under the [MIT License](LICENSE). Ignored private recordings, transcripts, manuscript materials, and working artifacts are not part of the repository or this license grant.
