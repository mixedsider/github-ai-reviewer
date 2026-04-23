# GitHub AI 자동 코드 리뷰어

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

GitHub Organization의 PR과 이슈가 생성될 때 AI가 자동으로 코드를 심층 분석하고 템플릿 기반 댓글을 작성하는 GitHub Actions 시스템입니다.

## 주요 기능

- **PR 자동 코드 리뷰** — 변경된 파일과 diff를 분석하여 버그, 보안 취약점, 성능 이슈를 감지
- **이슈 자동 응답** — 이슈 내용을 분류하고 초기 분석 댓글을 자동 작성
- **ORM 엔티티 변경 감지** — JPA, SQLAlchemy, Prisma, TypeORM 등 ORM 모델 변경 시 DB 심층 리뷰
- **다중 AI 제공자 지원** — Claude (Anthropic), GPT (OpenAI), 로컬 모델 (Ollama / LM Studio) 선택 가능
- **중복 댓글 방지** — 같은 PR에 새 커밋이 push되면 기존 봇 댓글을 업데이트

## 지원하는 AI 제공자

| 제공자 | `AI_PROVIDER` 값 | 필요 환경변수 |
|---|---|---|
| Anthropic Claude | `anthropic` | `ANTHROPIC_API_KEY` |
| OpenAI GPT | `openai` | `OPENAI_API_KEY` |
| Ollama / LM Studio | `local` | `LOCAL_MODEL_URL`, `LOCAL_MODEL_NAME` |

> 로컬 모델은 self-hosted GitHub Actions runner 환경에서만 동작합니다.

---

## 설치 및 배포 방법

이 저장소는 **Reusable Workflow** 방식으로 동작합니다. 리뷰어 코드는 이 저장소 한 곳에서 관리하고, Organization의 각 저장소는 워크플로우 파일 2개만 추가하면 됩니다.

```
[이 저장소] your-username/github-ai-reviewer   ← 리뷰어 코드 중앙 관리
        ↑ uses:
[각 저장소] org/repo-A   →  .github/workflows/pr-review.yml (2줄짜리 caller)
[각 저장소] org/repo-B   →  .github/workflows/pr-review.yml (동일)
```

### 1단계: 이 저장소를 GitHub에 push

```bash
git remote add origin https://github.com/your-username/github-ai-reviewer.git
git push -u origin main
```

> 저장소는 **public**이어야 합니다. private 저장소의 Reusable Workflow는 같은 Organization 내에서만 호출 가능합니다.

### 2단계: 이 저장소에 Secrets / Variables 설정

`Settings → Secrets and variables → Actions`에서 설정합니다.

**Secrets (민감한 API 키):**

| 이름 | 설명 |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API 키 (Claude 사용 시) |
| `OPENAI_API_KEY` | OpenAI API 키 (GPT 사용 시) |

**Variables (비민감한 설정값):**

| 이름 | 설명 | 예시 |
|---|---|---|
| `AI_PROVIDER` | 사용할 AI 제공자 | `anthropic` |
| `OPENAI_MODEL` | GPT 모델명 (선택사항) | `gpt-4o` |
| `LOCAL_MODEL_URL` | 로컬 모델 엔드포인트 | `http://localhost:11434` |
| `LOCAL_MODEL_NAME` | 로컬 모델명 | `llama3` |

### 3단계: 각 저장소에 caller 워크플로우 추가

`caller-examples/` 폴더의 파일 2개를 복사하여 각 저장소의 `.github/workflows/`에 추가합니다.

```bash
# 리뷰를 적용할 저장소로 이동
cd your-org/your-repo

mkdir -p .github/workflows
cp path/to/github-ai-reviewer/caller-examples/pr-review.yml .github/workflows/
cp path/to/github-ai-reviewer/caller-examples/issue-response.yml .github/workflows/
```

파일 안의 `your-username/github-ai-reviewer`를 실제 저장소 경로로 변경하세요.

```yaml
# .github/workflows/pr-review.yml (caller 예시)
jobs:
  review:
    uses: your-username/github-ai-reviewer/.github/workflows/pr-review.yml@main
    with:
      repository: ${{ github.repository }}
      pr_number: ${{ github.event.pull_request.number }}
    secrets:
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

### 4단계: 동작 확인

PR 또는 이슈를 생성하면 Actions 탭에서 워크플로우가 실행되고, 자동으로 봇 댓글이 달립니다.

---

## 로컬 테스트 방법

### 환경 설정

```bash
# 저장소 클론
git clone https://github.com/your-org/.github.git
cd .github

# 가상환경 생성
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r scripts/requirements.txt
```

### 테스트 실행

```bash
python -m pytest tests/ -v
```

### PR 리뷰 직접 실행

```bash
# .env.example을 복사하여 값 채우기
cp .env.example .env
# .env 파일 편집 후

# PR 리뷰 실행
export $(cat .env | grep -v '#' | xargs)
cd scripts
python review.py pr
```

### 이슈 응답 직접 실행

```bash
export $(cat .env | grep -v '#' | xargs)
cd scripts
python review.py issue
```

---

## 응답 템플릿 커스터마이징

`review-templates/` 폴더의 파일을 수정하여 봇 댓글 형식을 변경할 수 있습니다.

| 파일 | 용도 |
|---|---|
| `pr_review.md` | PR 리뷰 댓글 전체 형식 |
| `issue_response.md` | 이슈 응답 댓글 형식 |
| `db_review_section.md` | ORM 변경 감지 시 DB 섹션 형식 |

플레이스홀더는 `{{변수명}}` 형식입니다. 사용 가능한 변수 목록은 각 파일 안에 정의되어 있습니다.

---

## 지원하는 ORM DB 변경 감지

엔티티/모델 파일이 PR에 포함되면 자동으로 DB 심층 리뷰가 실행됩니다.

| ORM | 감지 대상 |
|---|---|
| JPA / Hibernate | `@Entity` 어노테이션이 포함된 `.java`, `.kt` 파일 |
| SQLAlchemy | `db.Model` 또는 `Base` 상속 `.py` 파일, `models.py` |
| Prisma | `schema.prisma` 파일 |
| Django ORM | `models.py` 파일 |
| TypeORM | `@Entity()` 어노테이션이 포함된 `.ts` 파일 |

DB 심층 체크 항목:
- 컬럼 추가 / 삭제 / 타입 변경
- 인덱스 변경
- 관계(FK, OneToMany 등) 변경
- 마이그레이션 파일 누락 여부
- N+1 위험 (Lazy loading fetch 전략 미설정)
- 컬럼 네이밍 컨벤션 위반
- NOT NULL 컬럼 기본값 누락

---

## 파일 구조

```
.github/
├── .github/
│   └── workflows/
│       ├── pr-review.yml        # PR 이벤트 트리거
│       └── issue-response.yml   # 이슈 이벤트 트리거
├── scripts/
│   ├── review.py                # 메인 실행 진입점
│   ├── github_client.py         # GitHub API 래퍼
│   ├── db_analyzer.py           # ORM 엔티티 변경 감지
│   ├── template_loader.py       # 템플릿 렌더링
│   ├── requirements.txt
│   └── providers/
│       ├── base.py              # 공통 AI 제공자 인터페이스
│       ├── anthropic_provider.py
│       ├── openai_provider.py
│       └── local_provider.py
├── review-templates/
│   ├── pr_review.md
│   ├── issue_response.md
│   └── db_review_section.md
└── tests/
    ├── test_providers.py
    ├── test_db_analyzer.py
    └── test_template_loader.py
```

---

## 제약사항

- 로컬 모델(Ollama/LM Studio)은 self-hosted runner 또는 외부에서 접근 가능한 URL이 필요합니다
- 매우 큰 PR(diff 80,000자 초과)은 일부가 생략되어 분석됩니다
- GitHub free 플랜의 private 저장소는 Actions 사용 시간 제한이 있습니다
