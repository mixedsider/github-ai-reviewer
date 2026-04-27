# GitHub AI Reviewer

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

English | [한국어](README.ko.md)

A reusable GitHub Actions workflow that automatically reviews pull requests and responds to newly opened issues with AI-generated comments.  
Add two workflow files to any repository and start using it immediately.

---

## Features

| Feature | Description |
|---|---|
| Automated PR review | Analyzes changed files and diffs to detect bugs, security risks, and performance issues |
| Automated issue response | Classifies new issues and writes an initial analysis comment |
| ORM change detection | Adds a deeper DB review when JPA, SQLAlchemy, Prisma, TypeORM, or similar model changes are detected |
| Multiple AI providers | Supports Claude, OpenAI models, and local models such as Ollama or LM Studio |
| Duplicate comment prevention | Updates the existing bot comment when new commits are pushed to the same PR |

---

## Quick Start

> **API keys are never shared with this repository.**  
> The workflow only uses the secrets configured in the repository where you install it.

### Step 1 — Add API Keys To Repository Secrets

In the repository where you want to enable reviews, go to `Settings → Secrets and variables → Actions`.

| Secret name | Required when |
|---|---|
| `ANTHROPIC_API_KEY` | Using Claude |
| `OPENAI_API_KEY` | Using OpenAI |

> **Organization-wide setup:** You can register these as Organization Secrets in `Organization → Settings → Secrets and variables → Actions` so multiple repositories can use them.

> **Repositories in the same organization:** You can use `secrets: inherit` if you do not want to list each secret explicitly.
> ```yaml
> secrets: inherit
> ```

---

### Step 2 — Add The PR Review Workflow

Create `.github/workflows/pr-review.yml`:

```yaml
name: AI PR Review

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
      reviewer_ref: "v1"                    # reviewer repository release ref
      # anthropic_model: "claude-sonnet-4-6"  # optional Claude model
      # openai_model: "gpt-4o"                # optional OpenAI model
      # local_model_url: "http://..."          # required for local models
      # local_model_name: "llama3"             # optional local model name
    secrets:
      GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

---

### Step 3 — Add The Issue Response Workflow

Create `.github/workflows/issue-response.yml`:

```yaml
name: AI Issue Response

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
      reviewer_ref: "v1"                    # reviewer repository release ref
      # anthropic_model: "claude-sonnet-4-6"  # optional Claude model
      # openai_model: "gpt-4o"                # optional OpenAI model
      # local_model_url: "http://..."          # required for local models
      # local_model_name: "llama3"             # optional local model name
    secrets:
      GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

---

### Step 4 — Verify It Works

Open a PR or an issue, then check the `Actions` tab. The bot will create or update a comment automatically.

---

## Supported AI Providers

| Provider | `ai_provider` value | Required secret |
|---|---|---|
| Anthropic Claude | `anthropic` | `ANTHROPIC_API_KEY` |
| OpenAI | `openai` | `OPENAI_API_KEY` |
| Ollama / LM Studio | `local` | — Requires a self-hosted runner or reachable endpoint |

**Supported Anthropic models (`anthropic_model`)**

| Model ID | Description |
|---|---|
| `claude-opus-4-7` | Strongest model |
| `claude-sonnet-4-6` | Default. Balanced speed and quality |
| `claude-haiku-4-5-20251001` | Fastest and most cost-effective model |

**Supported OpenAI models (`openai_model`)**

| Model ID | Description |
|---|---|
| `gpt-4o` | Default high-performance multimodal model |
| `gpt-4o-mini` | Faster and lower-cost model |

---

## Workflow Inputs

### PR Review (`pr-review.yml`)

| Input | Required | Default | Description |
|---|---|---|---|
| `repository` | ✅ | — | Repository that owns the PR, in `org/repo` format |
| `pr_number` | ✅ | — | Pull request number |
| `ai_provider` | — | `anthropic` | AI provider to use |
| `anthropic_model` | — | `claude-sonnet-4-6` | Claude model name |
| `openai_model` | — | `gpt-4o` | OpenAI model name |
| `local_model_url` | — | — | Local model endpoint URL |
| `local_model_name` | — | `llama3` | Local model name |
| `reviewer_ref` | — | `main` | Ref used to checkout this reviewer repository. When using a release, set this to the same ref as `uses` |

### Issue Response (`issue-response.yml`)

| Input | Required | Default | Description |
|---|---|---|---|
| `repository` | ✅ | — | Repository that owns the issue, in `org/repo` format |
| `issue_number` | ✅ | — | Issue number |
| `ai_provider` | — | `anthropic` | AI provider to use |
| `anthropic_model` | — | `claude-sonnet-4-6` | Claude model name |
| `openai_model` | — | `gpt-4o` | OpenAI model name |
| `local_model_url` | — | — | Local model endpoint URL |
| `local_model_name` | — | `llama3` | Local model name |
| `reviewer_ref` | — | `main` | Ref used to checkout this reviewer repository. When using a release, set this to the same ref as `uses` |

---

## ORM / DB Change Detection

When entity or model files are included in a PR, the workflow adds a deeper DB-focused review.

**Detected targets**

| ORM | Detection rule |
|---|---|
| JPA / Hibernate | `.java` or `.kt` files containing `@Entity` |
| SQLAlchemy | `.py` files inheriting from `db.Model` or `Base`, and `models.py` |
| Prisma | `schema.prisma` |
| Django ORM | `models.py` |
| TypeORM | `.ts` files containing `@Entity()` |

**Review checks**

- Column additions, deletions, and type changes
- Index changes
- Relationship changes such as FK, OneToMany, and ManyToMany
- Missing migrations
- N+1 query risks
- Column naming convention issues
- Missing defaults for NOT NULL columns

---

## Limitations

- Local models such as Ollama or LM Studio require a self-hosted runner or an externally reachable endpoint.
- Very large PRs are truncated after 80,000 diff characters before analysis.
- GitHub Free private repositories are subject to Actions usage limits.
