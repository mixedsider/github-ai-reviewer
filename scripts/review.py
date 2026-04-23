import os
import sys
import json
import re
import logging
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(__file__))

from github_client import GitHubClient
from db_analyzer import DBAnalyzer
from template_loader import TemplateLoader
from providers.anthropic_provider import AnthropicProvider
from providers.openai_provider import OpenAIProvider
from providers.local_provider import LocalProvider

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "review-templates")
MAX_DIFF_CHARS = 80000

PR_SYSTEM_PROMPT = """당신은 숙련된 시니어 개발자입니다. PR의 코드 변경사항을 심층적으로 리뷰하세요.
다음 항목을 반드시 분석하세요:
1. 전반적 코드 품질 평가
2. 버그 가능성 및 엣지 케이스
3. 보안 취약점 (SQL 인젝션, XSS, 인증/인가 문제 등)
4. 성능 이슈 (불필요한 반복, 메모리 누수 등)
5. 구체적인 개선 제안

응답은 반드시 JSON 형식으로 하세요:
{
  "overall_assessment": "전반적 평가 내용",
  "findings": "주요 발견사항 (마크다운 bullet point)",
  "security_performance": "보안/성능 이슈 내용",
  "suggestions": "제안사항 (마크다운 bullet point)"
}"""

ISSUE_SYSTEM_PROMPT = """당신은 친절한 개발팀 멤버입니다. 제출된 GitHub 이슈를 분석하고 초기 응답을 작성하세요.
응답은 반드시 JSON 형식으로 하세요:
{
  "issue_summary": "이슈 요약",
  "issue_category": "버그 / 기능 요청 / 질문 / 기타 중 하나",
  "initial_analysis": "초기 분석 내용",
  "next_steps": "권장 다음 단계 (마크다운 bullet point)"
}"""

DB_EXPERT_PROMPT = "당신은 데이터베이스 전문가입니다. ORM 엔티티/모델 변경사항을 분석하여 잠재적 문제점과 권장사항을 한국어로 작성하세요."


def get_provider():
    provider_name = os.environ.get("AI_PROVIDER", "anthropic").lower()
    if provider_name == "anthropic":
        return AnthropicProvider(api_key=os.environ["ANTHROPIC_API_KEY"])
    if provider_name == "openai":
        model = os.environ.get("OPENAI_MODEL", "gpt-4o")
        return OpenAIProvider(api_key=os.environ["OPENAI_API_KEY"], model=model)
    if provider_name == "local":
        return LocalProvider(
            base_url=os.environ["LOCAL_MODEL_URL"],
            model_name=os.environ.get("LOCAL_MODEL_NAME", "llama3"),
        )
    raise ValueError(f"알 수 없는 AI_PROVIDER: {provider_name}")


def parse_ai_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {}


def handle_pr():
    repo_name = os.environ["GITHUB_REPOSITORY"]
    pr_number = int(os.environ["PR_NUMBER"])

    client = GitHubClient(os.environ["GITHUB_TOKEN"])
    analyzer = DBAnalyzer()
    loader = TemplateLoader(TEMPLATES_DIR)
    provider = get_provider()

    logger.info("PR #%d 리뷰 시작 (%s)", pr_number, repo_name)
    diff, file_names = client.get_pr_diff(repo_name, pr_number)

    if len(diff) > MAX_DIFF_CHARS:
        diff = diff[:MAX_DIFF_CHARS] + "\n... (diff 크기 초과로 일부 생략됨)"

    db_changes = analyzer.detect_orm_changes(diff)

    user_content = f"변경 파일 목록:\n{chr(10).join(file_names)}\n\ndiff:\n{diff}"
    raw = provider.review_with_retry(PR_SYSTEM_PROMPT, user_content)
    ai_result = parse_ai_json(raw)

    db_review_text = "해당 없음"
    if db_changes["has_changes"]:
        logger.info("ORM 변경 감지: %s", db_changes["changed_files"])
        db_prompt = analyzer.build_db_review_prompt(db_changes)
        db_review_text = provider.review_with_retry(DB_EXPERT_PROMPT, db_prompt)

    changed_files_str = "\n".join(f"- `{f}`" for f in file_names)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    comment = loader.render("pr_review.md", {
        "changed_files_count": len(file_names),
        "changed_files": changed_files_str,
        "overall_assessment": ai_result.get("overall_assessment", raw),
        "findings": ai_result.get("findings", "분석 중 오류 발생"),
        "security_performance": ai_result.get("security_performance", "분석 중 오류 발생"),
        "db_review": db_review_text,
        "suggestions": ai_result.get("suggestions", "분석 중 오류 발생"),
        "ai_provider": provider.name,
        "reviewed_at": now,
    })

    client.post_pr_comment(repo_name, pr_number, comment)
    logger.info("PR #%d 리뷰 완료", pr_number)


def handle_issue():
    repo_name = os.environ["GITHUB_REPOSITORY"]
    issue_number = int(os.environ["ISSUE_NUMBER"])

    client = GitHubClient(os.environ["GITHUB_TOKEN"])
    loader = TemplateLoader(TEMPLATES_DIR)
    provider = get_provider()

    logger.info("이슈 #%d 응답 시작 (%s)", issue_number, repo_name)
    title, body = client.get_issue_body(repo_name, issue_number)
    user_content = f"제목: {title}\n\n내용:\n{body}"
    raw = provider.review_with_retry(ISSUE_SYSTEM_PROMPT, user_content)
    ai_result = parse_ai_json(raw)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    comment = loader.render("issue_response.md", {
        "issue_summary": ai_result.get("issue_summary", raw),
        "issue_category": ai_result.get("issue_category", "분류 중"),
        "initial_analysis": ai_result.get("initial_analysis", "분석 중 오류 발생"),
        "next_steps": ai_result.get("next_steps", "분석 중 오류 발생"),
        "ai_provider": provider.name,
        "reviewed_at": now,
    })

    client.post_issue_comment(repo_name, issue_number, comment)
    logger.info("이슈 #%d 응답 완료", issue_number)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "pr":
        handle_pr()
    elif mode == "issue":
        handle_issue()
    else:
        print("사용법: python review.py [pr|issue]")
        sys.exit(1)
