from scripts.review import (
    MAX_REVIEW_SECTION_CHARS,
    PR_SYSTEM_PROMPT,
    normalize_review_text,
    parse_ai_json,
    prepare_findings_section,
    prepare_review_section,
    strip_code_fences,
)


def test_pr_prompt_requires_conservative_evidence_based_review():
    assert "보수적으로" in PR_SYSTEM_PROMPT
    assert "diff에 직접 근거" in PR_SYSTEM_PROMPT
    assert "억지로 항목을 만들지" in PR_SYSTEM_PROMPT
    assert "최대 5개" in PR_SYSTEM_PROMPT
    assert "[심각]" in PR_SYSTEM_PROMPT
    assert "심각 > 위험 > 주의 > 일반" in PR_SYSTEM_PROMPT
    assert "코드블록" in PR_SYSTEM_PROMPT
    assert "500자 이내" in PR_SYSTEM_PROMPT


def test_normalize_review_text_collapses_empty_sections():
    assert normalize_review_text(None) == "없음"
    assert normalize_review_text("  해당 없음.  ") == "없음"
    assert normalize_review_text("No issues found") == "없음"


def test_normalize_review_text_formats_list_values():
    assert normalize_review_text(["첫 번째", "두 번째"]) == "- 첫 번째\n- 두 번째"


def test_parse_ai_json_handles_fenced_json():
    raw = """```json
{
  "overall_assessment": "좋습니다",
  "findings": "없음",
  "security_performance": "없음",
  "suggestions": "없음"
}
```"""

    result = parse_ai_json(raw, ["overall_assessment", "findings", "security_performance", "suggestions"])

    assert result["overall_assessment"] == "좋습니다"
    assert result["findings"] == "없음"


def test_parse_ai_json_recovers_jsonish_fields_with_multiline_values():
    raw = '''# 코드 리뷰 결과
{
  "overall_assessment": "중규모 변경입니다.",
  "findings": "## 주요 발견사항
- 실제 근거가 있는 항목입니다.",
  "security_performance": "없음",
  "suggestions": "테스트를 추가하세요."
}'''

    result = parse_ai_json(raw, ["overall_assessment", "findings", "security_performance", "suggestions"])

    assert result["overall_assessment"] == "중규모 변경입니다."
    assert "실제 근거" in result["findings"]
    assert result["security_performance"] == "없음"


def test_prepare_review_section_strips_code_fences_and_truncates():
    long_text = "```markdown\n" + ("가" * (MAX_REVIEW_SECTION_CHARS + 100)) + "\n```"

    result = prepare_review_section(long_text)

    assert "```" not in result
    assert "일부 생략됨" in result
    assert len(result) < len(long_text)


def test_strip_code_fences_removes_wrapping_fence():
    assert strip_code_fences("```json\n{\"a\": 1}\n```") == '{"a": 1}'


def test_prepare_findings_section_limits_to_five_and_sorts_by_level():
    raw = """
1. [일반] 네 번째입니다.
2. [주의] 세 번째입니다.
3. [심각] 첫 번째입니다.
4. [위험] 두 번째입니다.
5. [일반] 다섯 번째입니다.
6. [일반] 여섯 번째라 제외됩니다.
"""

    result = prepare_findings_section(raw)
    lines = result.splitlines()

    assert len(lines) == 5
    assert lines[0].startswith("- [심각]")
    assert lines[1].startswith("- [위험]")
    assert lines[2].startswith("- [주의]")
    assert lines[3].startswith("- [일반]")
    assert "여섯 번째" not in result


def test_prepare_findings_section_defaults_unlabeled_items_to_general():
    result = prepare_findings_section("- 라벨 없는 발견사항입니다.")

    assert result == "- [일반] 라벨 없는 발견사항입니다."
