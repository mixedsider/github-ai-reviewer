import re


ORM_CONTENT_PATTERNS = {
    r"src/.*\.java$": r"@Entity",
    r"src/.*\.kt$": r"@Entity",
    r".*/models?\.py$": None,
    r".*\.py$": r"(db\.Model|Base)",
    r".*/schema\.prisma$": None,
    r".*/entit(y|ies)/.*\.ts$": r"@Entity\(\)",
    r".*/entity/.*\.ts$": r"@Entity\(\)",
}

DB_REVIEW_PROMPT = """당신은 데이터베이스 전문가입니다. 다음 ORM 엔티티/모델 파일의 변경사항을 보수적으로 분석하세요.
체크리스트를 그대로 채우지 말고, diff에서 직접 근거가 있는 실질적인 DB 리스크만 작성하세요.

검토 대상:
- 컬럼 추가/삭제/타입 변경으로 인한 호환성 문제
- 인덱스 변경으로 인한 조회/쓰기 성능 문제
- 관계(FK, OneToMany, ManyToMany 등) 변경으로 인한 무결성 문제
- 마이그레이션 파일 누락 가능성
- 실제 접근 패턴이 드러난 N+1 위험
- 프로젝트 컨벤션과 명백히 충돌하는 컬럼 네이밍
- 기존 데이터가 있을 때 실패할 수 있는 NOT NULL/default 변경

작성 규칙:
- 문제가 확인되지 않으면 "없음"이라고만 답하세요.
- 가능성만으로 경고하지 마세요. diff에 근거가 있는 경우에만 작성하세요.
- 마이그레이션 누락은 스키마 변경이 있고 관련 마이그레이션 파일이 없을 때만 언급하세요.
- 최대 3개 항목만 작성하고, 각 항목은 근거와 영향을 한두 문장으로 설명하세요.
- 마크다운 제목, 표, 코드블록, 이모지, 심각도 라벨은 사용하지 마세요.
- 전체 답변은 700자 이내로 작성하세요.

변경된 파일: {changed_files}
함께 변경된 마이그레이션 파일: {migration_files}

diff 내용:
{diff_content}
"""

MIGRATION_FILE_PATTERNS = [
    r"(^|/)migrations?/.*",
    r"(^|/)db/migrate/.*",
    r"(^|/)alembic/versions/.*",
    r"(^|/)prisma/migrations/.*",
    r".*\.sql$",
]


class DBAnalyzer:
    def detect_orm_changes(self, full_diff: str) -> dict:
        changed_files = []
        current_file = None
        file_diff_map = {}
        lines = full_diff.splitlines()

        for line in lines:
            if line.startswith("+++ b/"):
                current_file = line[6:]
                file_diff_map[current_file] = []
            elif current_file is not None:
                file_diff_map[current_file].append(line)

        for filepath, diff_lines in file_diff_map.items():
            file_content = "\n".join(diff_lines)
            for file_pattern, content_pattern in ORM_CONTENT_PATTERNS.items():
                if re.search(file_pattern, filepath):
                    if content_pattern is None or re.search(content_pattern, file_content):
                        changed_files.append(filepath)
                        break

        orm_diff_parts = []
        for filepath in changed_files:
            orm_diff_parts.append(f"+++ b/{filepath}")
            orm_diff_parts.append("\n".join(file_diff_map[filepath]))

        migration_files = [
            filepath
            for filepath in file_diff_map
            if any(re.search(pattern, filepath) for pattern in MIGRATION_FILE_PATTERNS)
        ]

        return {
            "has_changes": len(changed_files) > 0,
            "changed_files": changed_files,
            "migration_files": migration_files,
            "diff_content": "\n".join(orm_diff_parts),
        }

    def build_db_review_prompt(self, changes: dict) -> str:
        return DB_REVIEW_PROMPT.format(
            changed_files=", ".join(changes["changed_files"]),
            migration_files=", ".join(changes.get("migration_files") or ["없음"]),
            diff_content=changes["diff_content"],
        )
