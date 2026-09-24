---
name: superoffice
description: Business-document maker for Korean managers and executives. Generates, reads, and converts docx/pptx/xlsx/hwpx/pdf cross-platform with company branding and gate-checked output. Use for /superoffice, weekly/quarterly reports, docx proposals, pptx decks, xlsx settlement sheets or KPI dashboards, hwpx official letters, applying a company template/brand kit, extracting tables from an existing document, or converting between those formats. Educational handouts route to supercontent.
---

# /superoffice - 직장인 업무 문서, 회사 브랜드로, 결론 먼저

Intent -> 형식 판별 -> 회사 브랜드 적용 -> 결론 먼저 메시지 구조 -> 결정론적 `office-gate` 통과. 기존 문서 한 줄 수정: skip this skill, edit directly.

## Core principles

- 결론 먼저. 팀장·경영자는 60초 안에 권고를 이해해야 한다 - BLUF/action title/한장보고. 색·레이아웃보다 메시지 구조가 먼저다 (`reference/biz-report.md`).
- 브리프 먼저 읽는다. 형식(docx/pptx/xlsx/hwpx/pdf)·대상·목적·분량·변환 타깃을 추론해 한 줄로 선언하고, 기본 템플릿이 아니라 그 브리프에 맞춘다.
- 회사 브랜드를 입힌다. 회사 템플릿 파일 상속 + brand-kit.json(색/폰트/로고/정책)을 한 번 캡처해 모든 형식에 일관 적용 (`reference/brand-kit.md`). 회사 색도 contrast AA를 지킨다.
- 검증은 눈대중이 아니다. 모든 산출물은 `templates/office-gate.sh`(safety+korean+integrity+contrast)를 통과한다. Builder는 자기 승인하지 않는다. 바이너리 산출물은 OfficeCLI(선택; `brew`/`scoop`/`npm`)가 있으면 렌더 검증(screenshot/issues/validate)으로 시각 결함까지 확인한다.
- 절대 위조하지 않는다. 없는 수치·날짜·통계는 `facts.json` 출처 또는 삭제. 라이브러리/변환 도구 부재 -> 문서화된 placeholder + `[substitution]`, 가짜 파일·가짜 렌더 금지.
- 협업 안전. 이모지 금지(대괄호 마커 `[현황]`/`[조치]`), 어절 띄어쓰기·맞춤법, 범용 한글 폰트(맑은 고딕/나눔). cross-platform 경로·폰트는 `templates/doc-env.py`에 위임.
- Hard stops. 외부 전송/게시, 회사 기밀 문서의 외부 서비스 업로드, 파괴적 단계는 명시적 동의.

## Mode (형식+작업으로 분류, 한 줄로 선언)

State e.g. `Making this as: PPTX 1분기 실적 보고 덱, 회사 브랜드 적용, 16:9, 12장`.

| Signal | Mode | Route |
|---|---|---|
| 보고서 / 제안서 / 기안 / 공문 본문 / docx | DOCX | `reference/docx.md` |
| 발표 덱 / 보고 슬라이드 / 정밀 표·도형 / pptx | PPTX | `reference/pptx.md` |
| 정산 / KPI / 대시보드 / 표·수식·차트 / 엑셀 / xlsx | XLSX | `reference/xlsx.md` |
| 한글 공문서 / 공공·기업 표준 / hwpx | HWPX | `reference/hwpx.md` |
| 다페이지 본문 PDF 생성 / PDF 읽기·표 추출 | PDF | `reference/pdf.md` |
| 기존 문서(docx/pptx/xlsx/pdf/hwpx) 읽기·표 추출 | READ | `reference/doc-ingest.md` |
| 형식 변환 / 마크다운 (hwpx<->docx<->pdf<->xlsx<->md) | CONVERT | 각 형식 reference의 변환 섹션 (`templates/doc-env.sh`); .md는 `reference/markdown.md` |

오버레이(빌드 모드 위에 얹음): **BRAND** 회사 템플릿/스타일 반영 -> `reference/brand-kit.md` (어느 빌드 모드든). **메시지 구조** 보고서·덱 -> `reference/biz-report.md` (보고 문서면 항상).

Tie-breaks: AI 초안 수업 덱·교육 자료 -> 이 레포 아님(supercontent). 단일면 인쇄 포스터 -> 이 레포 아님. "표 추출/읽어줘" -> READ. "변환만" -> CONVERT. 정밀 셀·좌표 .pptx vs 빠른 초안 -> 이 레포는 정밀(python-pptx)만.

## Default loop - role-separated

단순 단일 수정은 인라인으로 처리한다. 그 외에도 준비·작성은 직접 진행할 수 있으며, 문서 수만으로 producer를 늘리지 않는다. 사실·수식·변환·시각 결함의 위험이 큰 산출물은 fresh-context critic으로 독립 검증한다. 각 역할의 세부 계약은 해당 역할을 수행할 때만 읽는다. **Vault** = 문서당 작업 디렉토리, 기본 `.superoffice/<doc>/`: `doc-claims.md` + `facts.json` (+선택 `contrast-pairs.json`/`brand-kit.json`), `templates/`에서 시작. `office-gate.sh <vault> <text files>`가 이를 읽는다 - no vault, no gate.

1. **Read (브리프).** 형식·대상·목적·분량·변환 타깃·기밀 등급을 추론, 한 줄 선언. 두 해석이 갈리면 한 질문, 비대화형이면 보수적 가정 + 로그. vault 생성. (`reference/office.md`)
2. **Brand (오버레이, 필요 시).** 회사 자체 양식이 있으면 그 파일을 분석해 색·폰트·레이아웃을 추출하고 출처를 기록한다. 불명확하거나 기존 지침과 충돌하는 값만 확인해 brand-kit.json 확정; 없으면 `brand-interviewer`가 ≤5 질문으로 캡처. `.superoffice/brand-kit.json`에 저장해 재사용. 회사 양식은 형식 예시로도 쓴다(`reference/examples.md`). (`reference/brand-kit.md`, `agents/brand-interviewer.md`)
3. **Build.** docx/pptx/pdf/hwpx는 `doc-producer`, xlsx는 `xlsx-producer`. 메시지 구조는 `biz-report.md`, 디자인 팔레트는 형식 reference, 사용자가 형식/예시를 주면 그 구조를 따른다(`reference/examples.md`), 실제 자산만(위조 금지). `doc-claims.md` + `facts.json` 누적. 자기 승인 금지. (`agents/doc-producer.md`, `agents/xlsx-producer.md`)
4. **Critique (독립; 문서 무수정).** `doc-critic`이 본문/셀을 텍스트로 enumerate, `office-gate.sh` 실행, officecli 있으면 산출물을 PNG로 렌더해 육안 검수(텍스트 넘침·잔여 플레이스홀더; 부재 시 "렌더 미검증" 명시), 그다음 스크립트가 못 보는 것 판정: BLUF/action title/So-what/MECE, 한국어 자연스러움, 브랜드 일관성, 표·수치 정합. 모든 위반 로그. (`agents/doc-critic.md`)
5. **Verify.** 위반을 최소 수정하고 영향받은 게이트를 다시 실행한다. 통과는 명령 출력으로 보고한다. 동일 실패를 변경 없이 반복하지 말고 원인을 좁힌다. 유용한 범위 내 진전이 불가능한 실제 차단 조건에서 멈추고 필요한 입력과 미검증을 보고한다.

## Mode contract (deliverable + done-when)

| Mode | Deliverable | Verified by |
|---|---|---|
| DOCX / PPTX / XLSX / HWPX / PDF | 문서 파일 + vault (+변환 산출물) | `office-gate.sh` green (safety+korean+integrity, +contrast when pairs declared); 라이브러리/변환 부재 시 문서화된 placeholder |
| READ | 추출 텍스트/표(.txt/.csv/.md) + 출처 기록 | 형식별 파서로 추출; 스캔 PDF는 OCR 미적용 명시(위조 금지) |
| CONVERT | 변환 산출물 (또는 원본 + 수동 변환 안내) | 변환 직접 확인; H2Orestart 등 환경 변경은 동의 후 |
| BRAND (오버레이) | `.superoffice/brand-kit.json` | 스키마 유효 + 색이 contrast AA |

## Reference map (load only what the phase/mode needs)

| Read | When |
|---|---|
| `reference/office.md` | 시작: 형식/작업 판별 + 게이트 + vault + 환경 허브 |
| `reference/biz-report.md` | 보고서·덱: 결론 먼저 메시지 구조(BLUF/action title/SCQA/RAG) |
| `reference/brand-kit.md` | BRAND: 회사 템플릿 상속 + brand-kit.json 인터뷰·적용 |
| `reference/examples.md` | 형식 따라하기: 하우스 견본 + 사용자 예시/회사 양식 구조 모방 |
| `reference/docx.md` | DOCX 빌드/읽기 (python-docx) |
| `reference/pptx.md` | PPTX 빌드/읽기 (python-pptx, 정밀 제어 + 덱 디자인) |
| `reference/xlsx.md` | XLSX 빌드/읽기 (openpyxl/XlsxWriter/pandas) |
| `reference/hwpx.md` | HWPX 빌드/편집/읽기/검증 (python-hwpx) |
| `reference/pdf.md` | PDF 생성/읽기 (Chromium/WeasyPrint/ReportLab; pdfplumber/pypdf) |
| `reference/doc-ingest.md` | READ: 형식 무관 기존 문서 읽기 매트릭스 |
| `reference/markdown.md` | 마크다운 <-> office 변환·추출 (.md 소스/산출) |
| `reference/sources.md` | 라이브러리·라이선스·attribution |

## Final checklist

- [ ] Mode + 한 줄 Read 선언; 형식·대상·목적·변환 타깃이 브리프에
- [ ] 회사 브랜드 필요 시 brand-kit 적용(템플릿 상속 또는 인터뷰); 브랜드 색 contrast AA
- [ ] 메시지 구조 먼저(`biz-report.md`): 결론 먼저, action title, 한장보고; 그다음 디자인 팔레트
- [ ] 이모지 없음, 어절 띄어쓰기·맞춤법, 범용 한글 폰트; cross-platform은 `doc-env.py` 위임
- [ ] 실제/생성 자산만(위조 없음), 수치·날짜는 `facts.json` 출처
- [ ] Mode contract 충족: 빌드 모드 -> `templates/office-gate.sh` green(출력 보고) + critic HIGH 0건
- [ ] 바이너리 산출물은 officecli 있으면 렌더 PNG 육안 검수(텍스트 넘침·잔여 플레이스홀더 없음); 부재 시 "렌더 미검증" 명시
- [ ] 의도에 대한 최소 변경; 요청 없는 재작성 없음
- [ ] 외부 전송/게시·기밀 외부 업로드·파괴적 단계는 명시적 동의
