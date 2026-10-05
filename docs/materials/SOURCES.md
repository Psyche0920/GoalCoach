# Verified pilot sources and acquisition boundaries

Verified on **2026-10-02** against live public endpoints. The pilot is adult beginner Mandarin greetings and self-introduction. Source access, source licensing, teaching accuracy and permission to publish are separate decisions.

## Real acquisition completed

An independent workbench at `materials-workspace/source-verification/workbench.db` contains **87 actual evidence spans from two real sources**. The directory is ignored by Git. No model calls, teaching approvals or releases were created for this verification.

Native PDF ingestion was then implemented and verified independently in `materials-workspace/source-verification/pdf-validation.db`. The production PDF importer read the same MIT page directly and produced **41 spans**, all bound to the original PDF SHA-256 and `page=18` locators. This is a second validation of the same material, not 41 additional unique source passages. Its audit is `pdf-verification.json`. The initial extracted-text path used the bundled document runtime; the production path uses the pinned project dependency, so line segmentation differs.

| Source | Exact edition and acquisition | Evidence | Use registered |
| --- | --- | --- | --- |
| [MIT OpenCourseWare, Learning Chinese: A Foundation Course in Mandarin](https://ocw.mit.edu/courses/res-21g-003-learning-chinese-a-foundation-course-in-mandarin-spring-2011/) | Julian K. Wheatley, Unit 1 dated **4/07**, in the Spring 2011 online resource. Official PDF downloaded, 432,734 bytes / 25 pages; **only PDF page 18, printed page 51**, extracted and visually checked. This is not the later Yale print edition. | 43 spans; greetings, leave-taking, pinyin, English meanings and usage notes | Local noncommercial analysis only |
| [Wikibooks, Chinese (Mandarin)/Greetings, revision 3967819](https://en.wikibooks.org/w/index.php?title=Chinese_(Mandarin)/Greetings&oldid=3967819) | Actual fixed-revision HTML acquired through the production HTTPS collector, with navigation removed and table boundaries preserved | 44 spans | Analysis only; explicitly a community reference, not an official curriculum |

The MIT [resource page](https://ocw.mit.edu/courses/res-21g-003-learning-chinese-a-foundation-course-in-mandarin-spring-2011/resources/mitres_21g_003s11_unit01/), PDF attribution page and [current terms](https://ocw.mit.edu/pages/privacy-and-terms-of-use/) were checked. The terms specify **CC BY-NC-SA 4.0**, including attribution, noncommercial use, ShareAlike and third-party exceptions. The Wikibooks license footer specifies **CC BY-SA 4.0** and additional applicable terms. Both registrations permit only `analysis`; neither grants adaptation, redistribution, commercial publication, model training or human teaching approval.

Attribution must retain authors/contributors, source and revision URLs, license links and change notices. For the validation sample, extraction/HTML cleanup are the recorded changes. Automated `approved_by` values in the example source records describe a source-license check; they are not a teacher's review or a legal opinion. The material remains subject to the normal evidence, independent review and human approval gates.

The full audit is `materials-workspace/source-verification/verification.json`, alongside the raw PDF, extracted one-page text, rendered page, fetched HTML and YouTube metadata. Audit checksums:

| Artifact | SHA-256 |
| --- | --- |
| MIT original PDF | `e4ed6d757e3d24643638f35df3e4ff26640ec720dace721df5756b00efad254a` |
| MIT extracted page text | `cde334d4b920a099e148dba29664f2740cc3bf6242bbc7300da47d5befc56242` |
| Wikibooks fetched HTML | `95e0f86042fe66319f1b47c9838db02fa537e77c8e961fa8082825d56566e3ee` |
| Wikibooks cleaned text | `0a08c0d7382179d33e9bcb13e6737cd04d41c8934094dd73722b22d3042be7d7` |

Fetched HTML includes presentation that may change on a later fetch; its checksum identifies this actual response, while the revision URL identifies the article revision. Span `source_hash` identifies the imported text, and the audit separately preserves original-download hashes.

## Official framework and historical candidates

- [ChineseTest HSK](https://www.chinesetest.cn/HSK) returned HTTP 200. This verifies the official reference endpoint, not a particular syllabus edition or permission to reproduce a commercial *HSK Standard Course* textbook. No commercial textbook was imported.
- [ERIC ED187091](https://eric.ed.gov/?id=ED187091) returned HTTP 200 and identifies *Standard Chinese: A Modular Approach. Student Text. Module 1: Orientation; Module 2: Biographic Information*, August 1979, by the Defense Language Institute, Monterey, CA. It remains a historical candidate: a government catalog entry alone does not establish public-domain status of every element. No FSI/DLI corpus or rights approval is claimed.

Machine-readable selection and decisions are in `examples/materials/sources/pilot-registry.json`. The two `*-analysis.json` files are valid source registrations for this limited pilot purpose.

## YouTube and Bilibili

**YouTube metadata works live.** The official public oEmbed endpoint returned the authentic author **Mandarin Corner**, its channel URL and the title for [this video](https://www.youtube.com/watch?v=vTVuuJ5xBco). The video concerns the economy, so it serves only to verify the connector; it is not beginner Mandarin evidence. The connector discards embed HTML and returns typed metadata with `content_permission: not_granted_by_metadata`.

**YouTube subtitles require authorization.** An anonymous request to the official `captions.list` endpoint returned HTTP 403. The [official captions.download documentation](https://developers.google.com/youtube/v3/docs/captions/download) explicitly requires authorization and permission to edit the video. No YouTube transcript was downloaded. An API key alone does not create ownership or transcript reuse rights. Obtain a creator-authorized SRT/VTT export or an appropriately authorized platform export, then import it with a truthful source record.

**Bilibili live automated access is blocked.** The [developer portal](https://open.bilibili.com/doc) returned HTTP 200, while the pilot [public channel URL](https://space.bilibili.com/456664753) returned HTTP 200 with a CAPTCHA page titled `验证码_哔哩哔哩`. A 200 status is therefore not proof of usable source access. The channel identity was not asserted from the CAPTCHA response. No bypass or undocumented subtitle API was used.

For ordinary Bilibili video URLs, the connector accepts only complete static title/author metadata. CAPTCHA pages and missing metadata fail explicitly. This path is tested with fixtures; successful live Bilibili video metadata collection has not been claimed. Creator-owned Bilibili JSON exports in the usual `body: [{from, to, content}]` shape can be imported. Rights still come from the source registration, not the file format.

## Operator commands

```sh
# Public metadata only: does not register or approve curriculum evidence.
.venv/bin/python -m goalcoach.materials source-metadata 'https://www.youtube.com/watch?v=vTVuuJ5xBco'

# Repeat the open-reference collection into an isolated workbench.
.venv/bin/python -m goalcoach.materials --db materials-workspace/source-verification/workbench.db collect --source examples/materials/sources/wikibooks-greetings-analysis.json --allow-host en.wikibooks.org

# Import the verified PDF page directly into the independent PDF validation workbench.
.venv/bin/python -m goalcoach.materials --db materials-workspace/source-verification/pdf-validation.db import --source examples/materials/sources/mit-unit01-analysis.json --file materials-workspace/source-verification/MITRES_21G_003S11_unit01.pdf --pdf-page 18

# Use only an actual creator-authorized export and corresponding verified source.
.venv/bin/python -m goalcoach.materials import --source path/to/verified-source.json --file path/to/authorized-subtitles.vtt --subtitles
```

The generic network collector handles HTML and UTF-8 text. Native-text PDFs are imported from explicitly authorized local files with one or more `--pdf-page` selections. Input is limited to 20 MB, 20 distinct 1-based selected pages and 1 MB of cumulative extracted text. Invalid, encrypted, out-of-range and text-empty/image-only pages fail explicitly; no source or spans are registered until every selected page passes. Original PDF hashes and page/line/offset locators are retained. OCR is not implemented; scanned sources require a separately authorized and reviewed text export. Subtitle ingestion supports SRT, WebVTT and Bilibili JSON, rejects malformed timings and empty cues, retains original-file hashes and attaches cue/time locators to the cleaned evidence.

## Collector guarantees and limits

- HTTPS only, exact allowlisted hosts, no embedded credentials, IP literals, fragments, nonstandard ports or redirects.
- DNS resolution must yield only globally routable addresses. The connection is pinned to a validated address with the original hostname supplied for TLS certificate verification and SNI, preventing a second DNS lookup from rebinding the request.
- One-megabyte decompressed response limit, strict response media types, 200-only complete responses, a 20-second I/O timeout and 25-second total deadline.
- Static HTML cleanup prefers semantic main content, removes script/navigation regions, preserves table column separators and redacts email addresses. It is not complete personal-data anonymization or a universal content extractor.
- No cookies, login replay, CAPTCHA solving, video downloads, private platform endpoints or automatic source-rights approval. Network response bodies and platform embeds are not executable instructions.

Source-boundary tests cover private/multicast/reserved DNS, mixed public/private DNS, invalid URLs, address pinning/SNI, redirects, partial responses, oversized bodies, untrusted metadata, CAPTCHA handling, text extraction, subtitle formats, timestamp validity, original hashes and source permission enforcement. PDF tests additionally cover explicit page selection, native extraction, binary hashes, encryption, malformed PDFs, missing/image-only pages, size/extraction limits and rejection without partial registration. Live external services are deliberately not part of deterministic CI.
