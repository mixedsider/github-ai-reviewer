# GitHub AI 자동 코드 리뷰어

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

PR과 이슈가 생성될 때 AI가 자동으로 코드를 심층 분석하고 댓글을 작성하는 GitHub Actions Reusable Workflow입니다.  
워크플로우 파일 2개만 추가하면 **어떤 저장소에서든 즉시 사용**할 수 있습니다.

---

## 주요 기능

| 기능 | 설명 |
|---|---|
| PR 자동 코드 리뷰 | 변경된 파일과 diff를 분석하여 버그, 보안 취약점, 성능 이슈를 감지 |
| 이슈 자동 응답 | 이슈 내용을 분류하고 초기 분석 댓글을 자동 작성 |
| ORM 변경 감지 | JPA, SQLAlchemy, Prisma, TypeORM 등 모델 변경 시 DB 심층 리뷰 자동 실행 |
| 다중 AI 제공자 | Claude, GPT, 로컬 모델(Ollama / LM Studio) 중 선택 가능 |
| 중복 댓글 방지 | 같은 PR에 새 커밋이 push되면 기존 봇 댓글을 업데이트 |

---

## 빠른 시작

> **API 키는 이 저장소와 공유되지 않습니다.**  
> 각자의 저장소 Secrets에 등록한 키만 사용됩니다.

### Step 1 — API 키를 저장소 Secrets에 등록

리뷰를 적용할 저장소에서 `Settings → Secrets and variables → Actions`로 이동합니다.

| Secret 이름 | 등록 조건 |
|---|---|
| `ANTHROPIC_API_KEY` | Claude 사용 시 |
| `OPENAI_API_KEY` | GPT 사용 시 |

> **Organization 단위 일괄 적용:** `Organization → Settings → Secrets and variables → Actions`에서 Organization Secret으로 등록하면 모든 저장소에 자동 적용됩니다.

> **같은 Organization 내 저장소:** 워크플로우에서 `secrets: inherit`을 사용하면 Secrets를 명시적으로 나열할 필요가 없습니다.
> ```yaml
> secrets: inherit
> ```

---

### Step 2 — PR 리뷰 워크플로우 추가

`.github/workflows/pr-review.yml` 파일을 아래 내용으로 생성합니다.

```yaml
name: AI PR 코드 리뷰

on:
  pull_request:
    types: [opened, synchronize, reopened]

permissions:
  pull-requests: write
  contents: read

jobs:
  review:
    uses: mixedsider/github-ai-reviewer/.github/workflows/pr-review.yml@v1
    with:
      repository: ${{ github.repository }}
      pr_number: ${{ github.event.pull_request.number }}
      ai_provider: "anthropic"              # anthropic / openai / local
      reviewer_ref: "v1"                    # 리뷰어 저장소 릴리스 ref
      # anthropic_model: "claude-sonnet-4-6"  # Claude 모델 선택 (선택)
      # openai_model: "gpt-4o"                # OpenAI 사용 시 (선택)
      # local_model_url: "http://..."          # 로컬 모델 사용 시 (선택)
      # local_model_name: "llama3"             # 로컬 모델 사용 시 (선택)
    secrets:
      GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

---

### Step 3 — 이슈 응답 워크플로우 추가

`.github/workflows/issue-response.yml` 파일을 아래 내용으로 생성합니다.

```yaml
name: AI 이슈 자동 응답

on:
  issues:
    types: [opened]

permissions:
  issues: write
  contents: read

jobs:
  respond:
    uses: mixedsider/github-ai-reviewer/.github/workflows/issue-response.yml@v1
    with:
      repository: ${{ github.repository }}
      issue_number: ${{ github.event.issue.number }}
      ai_provider: "anthropic"              # anthropic / openai / local
      reviewer_ref: "v1"                    # 리뷰어 저장소 릴리스 ref
      # anthropic_model: "claude-sonnet-4-6"  # Claude 모델 선택 (선택)
      # openai_model: "gpt-4o"                # OpenAI 사용 시 (선택)
      # local_model_url: "http://..."          # 로컬 모델 사용 시 (선택)
      # local_model_name: "llama3"             # 로컬 모델 사용 시 (선택)
    secrets:
      GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

---

### Step 4 — 동작 확인

PR 또는 이슈를 생성하면 `Actions` 탭에서 워크플로우가 실행되고, 자동으로 봇 댓글이 작성됩니다.

---

## 지원하는 AI 제공자

| 제공자 | `ai_provider` 값 | 필요 Secret |
|---|---|---|
| Anthropic Claude | `anthropic` | `ANTHROPIC_API_KEY` |
| OpenAI GPT | `openai` | `OPENAI_API_KEY` |
| Ollama / LM Studio | `local` | — (self-hosted runner 필요) |

**Anthropic 사용 가능한 모델 (`anthropic_model`)**

| 모델 ID | 설명 |
|---|---|
| `claude-opus-4-7` | 가장 강력한 모델 |
| `claude-sonnet-4-6` | 기본값. 성능과 속도의 균형 |
| `claude-haiku-4-5-20251001` | 가장 빠르고 저렴한 모델 |

**OpenAI 사용 가능한 모델 (`openai_model`)**

| 모델 ID | 설명 |
|---|---|
| `gpt-4o` | 기본값. 고성능 멀티모달 모델 |
| `gpt-4o-mini` | 빠르고 저렴한 모델 |

---

## 워크플로우 입력값 전체 목록

### PR 리뷰 (`pr-review.yml`)

| 입력값 | 필수 | 기본값 | 설명 |
|---|---|---|---|
| `repository` | ✅ | — | PR이 속한 저장소 (`org/repo` 형식) |
| `pr_number` | ✅ | — | PR 번호 |
| `ai_provider` | — | `anthropic` | 사용할 AI 제공자 |
| `anthropic_model` | — | `claude-sonnet-4-6` | Claude 모델명 |
| `openai_model` | — | `gpt-4o` | OpenAI 모델명 |
| `local_model_url` | — | — | 로컬 모델 엔드포인트 URL |
| `local_model_name` | — | `llama3` | 로컬 모델명 |
| `reviewer_ref` | — | `main` | 리뷰어 저장소 체크아웃 ref. 릴리스 사용 시 `uses`의 ref와 동일하게 지정 |

### 이슈 응답 (`issue-response.yml`)

| 입력값 | 필수 | 기본값 | 설명 |
|---|---|---|---|
| `repository` | ✅ | — | 이슈가 속한 저장소 (`org/repo` 형식) |
| `issue_number` | ✅ | — | 이슈 번호 |
| `ai_provider` | — | `anthropic` | 사용할 AI 제공자 |
| `anthropic_model` | — | `claude-sonnet-4-6` | Claude 모델명 |
| `openai_model` | — | `gpt-4o` | OpenAI 모델명 |
| `local_model_url` | — | — | 로컬 모델 엔드포인트 URL |
| `local_model_name` | — | `llama3` | 로컬 모델명 |
| `reviewer_ref` | — | `main` | 리뷰어 저장소 체크아웃 ref. 릴리스 사용 시 `uses`의 ref와 동일하게 지정 |

---

## ORM DB 변경 감지

엔티티/모델 파일이 PR에 포함되면 자동으로 DB 심층 리뷰가 추가됩니다.

**감지 대상**

| ORM | 감지 조건 |
|---|---|
| JPA / Hibernate | `@Entity` 어노테이션이 포함된 `.java`, `.kt` 파일 |
| SQLAlchemy | `db.Model` / `Base` 상속 `.py` 파일, `models.py` |
| Prisma | `schema.prisma` 파일 |
| Django ORM | `models.py` 파일 |
| TypeORM | `@Entity()` 어노테이션이 포함된 `.ts` 파일 |

**체크 항목**

- 컬럼 추가 / 삭제 / 타입 변경
- 인덱스 변경
- 관계 (FK, OneToMany 등) 변경
- 마이그레이션 파일 누락
- N+1 위험 (Lazy loading fetch 전략 미설정)
- 컬럼 네이밍 컨벤션 위반
- NOT NULL 컬럼 기본값 누락

---

## 제약사항

- 로컬 모델 (Ollama / LM Studio)은 self-hosted runner 또는 외부에서 접근 가능한 URL이 필요합니다
- 매우 큰 PR (diff 80,000자 초과)은 일부가 생략되어 분석됩니다
- GitHub Free 플랜의 private 저장소는 Actions 사용 시간 제한이 있습니다
