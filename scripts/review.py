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
MAX_REVIEW_SECTION_CHARS = 1800
MAX_DB_REVIEW_CHARS = 1400

PR_SYSTEM_PROMPT = """당신은 숙련된 시니어 개발자입니다. PR의 코드 변경사항을 리뷰하세요.
리뷰는 보수적으로 작성하세요. diff에 직접 근거가 있는 실질적인 문제만 지적하고, 일반론/추측/취향/사소한 스타일 지적은 남기지 마세요.

리뷰 기준:
1. 변경된 코드에서 재현 가능한 버그, 명확한 엣지 케이스 누락, 보안 취약점, 의미 있는 성능 저하만 주요 발견사항으로 작성하세요.
2. 보안/성능 이슈는 diff 안에서 위험 경로가 확인될 때만 작성하세요. 확인되지 않으면 "없음"이라고 쓰세요.
3. 테스트 제안은 변경된 동작의 회귀 위험을 줄이는 구체적인 테스트가 있을 때만 작성하세요.
4. 문제가 없으면 억지로 항목을 만들지 말고 findings, security_performance, suggestions에 모두 "없음"이라고 쓰세요.
5. 발견사항은 최대 5개로 제한하고, 각 항목은 근거와 영향이 드러나도록 한두 문장으로 작성하세요.
6. 심각도를 과장하지 마세요. 확실하지 않은 내용은 지적하지 말고 생략하세요.
7. 마크다운 제목, 표, 코드블록, 이모지, 심각도 라벨(Critical/High/Medium/Low)을 사용하지 마세요.
8. 각 JSON 값은 500자 이내로 작성하세요.

응답은 반드시 JSON 형식으로만 하세요:
{
  "overall_assessment": "변경 범위와 전반적 위험도를 짧게 평가",
  "findings": "주요 발견사항. 없으면 없음",
  "security_performance": "보안/성능 이슈. 없으면 없음",
  "suggestions": "구체적인 개선 제안. 없으면 없음"
}"""

ISSUE_SYSTEM_PROMPT = """당신은 친절한 개발팀 멤버입니다. 제출된 GitHub 이슈를 분석하고 초기 응답을 작성하세요.
응답은 반드시 JSON 형식으로 하세요:
{
  "issue_summary": "이슈 요약",
  "issue_category": "버그 / 기능 요청 / 질문 / 기타 중 하나",
  "initial_analysis": "초기 분석 내용",
  "next_steps": "권장 다음 단계 (마크다운 bullet point)"
}"""

DB_EXPERT_PROMPT = "당신은 데이터베이스 전문가입니다. ORM 엔티티/모델 변경사항을 보수적으로 분석하고, diff에서 직접 근거가 있는 실질적인 DB 리스크만 한국어로 짧게 작성하세요. 문제가 확인되지 않으면 '없음'이라고 답하세요. 마크다운 제목, 표, 코드블록, 이모지, 심각도 라벨은 사용하지 말고 700자 이내로 답하세요."

EMPTY_SECTION_VALUES = {
    "",
    "없음",
    "해당 없음",
    "없습니다",
    "문제 없음",
    "특이사항 없음",
    "발견된 문제 없음",
    "n/a",
    "none",
    "no issues",
    "no issues found",
}


def normalize_review_text(value, empty_text: str = "없음") -> str:
    if value is None:
        return empty_text
    if isinstance(value, list):
        value = "\n".join(f"- {item}" for item in value if str(item).strip())
    elif isinstance(value, dict):
        value = json.dumps(value, ensure_ascii=False)
    else:
        value = str(value)

    value = value.strip()
    normalized = re.sub(r"[\s\.\!]+", " ", value).strip().lower()
    if normalized in EMPTY_SECTION_VALUES:
        return empty_text
    return value


def prepare_review_section(value, empty_text: str = "없음", max_chars: int = MAX_REVIEW_SECTION_CHARS) -> str:
    text = normalize_review_text(value, empty_text)
    return truncate_review_text(text, max_chars)


def strip_code_fences(text: str) -> str:
    text = text.strip()
    fenced = re.fullmatch(r"```[A-Za-z0-9_-]*\s*(.*?)\s*```", text, flags=re.DOTALL)
    if fenced:
        return fenced.group(1).strip()
    return re.sub(r"```[A-Za-z0-9_-]*\s*|\s*```", "", text).strip()


def truncate_review_text(text: str, max_chars: int) -> str:
    text = strip_code_fences(str(text)).strip()
    if len(text) <= max_chars:
        return text

    truncated = text[:max_chars].rstrip()
    last_break = max(truncated.rfind("\n"), truncated.rfind(". "), truncated.rfind("다."))
    if last_break >= max_chars * 0.6:
        truncated = truncated[:last_break + 1].rstrip()
    return f"{truncated}\n\n...(응답이 길어 일부 생략됨)"


def _decode_jsonish_string(value: str) -> str:
    value = value.strip()
    try:
        return json.loads(f'"{value}"')
    except json.JSONDecodeError:
        return (
            value
            .replace(r"\"", '"')
            .replace(r"\n", "\n")
            .replace(r"\t", "\t")
            .replace(r"\\", "\\")
        ).strip()


def _extract_jsonish_fields(text: str, keys: list[str]) -> dict:
    result = {}
    for idx, key in enumerate(keys):
        following_keys = keys[idx + 1:]
        if following_keys:
            next_key_pattern = "|".join(re.escape(next_key) for next_key in following_keys)
            boundary = rf'(?="\s*,?\s*\n?\s*"(?:{next_key_pattern})"\s*:)'
        else:
            boundary = r'(?="\s*,?\s*\n?\s*\})'

        match = re.search(rf'"{re.escape(key)}"\s*:\s*"(.*?){boundary}', text, flags=re.DOTALL)
        if match:
            result[key] = _decode_jsonish_string(match.group(1))
    return result


def get_provider():
    provider_name = (os.environ.get("AI_PROVIDER") or "anthropic").lower()
    if provider_name == "anthropic":
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            sys.exit("오류: ANTHROPIC_API_KEY가 설정되지 않았습니다. 저장소의 Secrets에 ANTHROPIC_API_KEY를 등록해 주세요.")
        model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
        return AnthropicProvider(api_key=api_key, model=model)
    if provider_name == "openai":
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            sys.exit("오류: OPENAI_API_KEY가 설정되지 않았습니다. 저장소의 Secrets에 OPENAI_API_KEY를 등록해 주세요.")
        model = os.environ.get("OPENAI_MODEL", "gpt-4o")
        return OpenAIProvider(api_key=api_key, model=model)
    if provider_name == "local":
        base_url = os.environ.get("LOCAL_MODEL_URL")
        if not base_url:
            sys.exit("오류: LOCAL_MODEL_URL이 설정되지 않았습니다. 워크플로우 입력값에 local_model_url을 지정해 주세요.")
        return LocalProvider(
            base_url=base_url,
            model_name=os.environ.get("LOCAL_MODEL_NAME", "llama3"),
        )
    sys.exit(f"오류: 알 수 없는 AI_PROVIDER '{provider_name}'. anthropic / openai / local 중 하나를 입력하세요.")


def parse_ai_json(text: str, expected_keys: list[str] | None = None) -> dict:
    text = strip_code_fences(text)
    candidates = [text]

    fenced_blocks = re.findall(r"```[A-Za-z0-9_-]*\s*(.*?)\s*```", text, flags=re.DOTALL)
    candidates.extend(fenced_blocks)

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidates.append(text[start:end + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate.strip())
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue

    if expected_keys:
        recovered = _extract_jsonish_fields(text, expected_keys)
        if recovered:
            logger.warning("AI 응답 JSON 파싱 실패. 일부 필드를 복구했습니다.")
            return recovered

    logger.warning("AI 응답에서 JSON 파싱 실패. 원본 텍스트를 사용합니다.")
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
    pr_keys = ["overall_assessment", "findings", "security_performance", "suggestions"]
    ai_result = parse_ai_json(raw, pr_keys)

    db_review_text = "해당 없음"
    if db_changes["has_changes"]:
        logger.info("ORM 변경 감지: %s", db_changes["changed_files"])
        db_prompt = analyzer.build_db_review_prompt(db_changes)
        db_raw = provider.review_with_retry(DB_EXPERT_PROMPT, db_prompt)
        changed_entity_files_str = "\n".join(f"- `{f}`" for f in db_changes["changed_files"])
        db_review_text = loader.render("db_review_section.md", {
            "changed_entity_files": changed_entity_files_str,
            "db_changes": "diff 내 ORM 엔티티 변경 감지",
            "db_check_results": prepare_review_section(db_raw, "없음", MAX_DB_REVIEW_CHARS),
        })

    changed_files_str = "\n".join(f"- `{f}`" for f in file_names)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    comment = loader.render("pr_review.md", {
        "changed_files_count": len(file_names),
        "changed_files": changed_files_str,
        "overall_assessment": prepare_review_section(ai_result.get("overall_assessment"), "분석 결과를 구조화하지 못했습니다."),
        "findings": prepare_review_section(ai_result.get("findings"), "없음"),
        "security_performance": prepare_review_section(ai_result.get("security_performance"), "없음"),
        "db_review": db_review_text,
        "suggestions": prepare_review_section(ai_result.get("suggestions"), "없음"),
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
    issue_keys = ["issue_summary", "issue_category", "initial_analysis", "next_steps"]
    ai_result = parse_ai_json(raw, issue_keys)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    comment = loader.render("issue_response.md", {
        "issue_summary": prepare_review_section(ai_result.get("issue_summary"), "이슈 내용을 구조화하지 못했습니다."),
        "issue_category": prepare_review_section(ai_result.get("issue_category"), "분류 중", 200),
        "initial_analysis": prepare_review_section(ai_result.get("initial_analysis"), "분석 중 오류 발생"),
        "next_steps": prepare_review_section(ai_result.get("next_steps"), "없음"),
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
