import re


ORM_FILE_PATTERNS = [
    r"src/.*\.java$",
    r"src/.*\.kt$",
    r".*/models?\.py$",
    r".*\.py$",
    r".*/schema\.prisma$",
    r".*\.ts$",
]

ORM_CONTENT_PATTERNS = {
    r"src/.*\.java$": r"@Entity",
    r"src/.*\.kt$": r"@Entity",
    r".*/models?\.py$": None,
    r".*\.py$": r"(db\.Model|Base)",
    r".*/schema\.prisma$": None,
    r".*\.ts$": r"@Entity\(\)",
}

DB_REVIEW_PROMPT = """당신은 데이터베이스 전문가입니다. 다음 ORM 엔티티/모델 파일의 변경사항을 분석하고 아래 항목을 체크하세요:

1. 컬럼 추가/삭제/타입 변경 여부
2. 인덱스 변경 여부
3. 관계(FK, OneToMany, ManyToMany 등) 변경 여부
4. 마이그레이션 파일 누락 가능성
5. N+1 위험 (Lazy loading 관계에 fetch 전략 미설정)
6. 컬럼 네이밍 컨벤션 위반 (snake_case 권장)
7. NOT NULL 컬럼에 기본값 누락

변경된 파일: {changed_files}

diff 내용:
{diff_content}

각 항목에 대해 발견된 문제점과 권장사항을 한국어로 명확하게 작성하세요."""


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
                    if content_pattern is None or re.search(content_pattern, full_diff):
                        changed_files.append(filepath)
                        break

        return {
            "has_changes": len(changed_files) > 0,
            "changed_files": changed_files,
            "diff_content": full_diff,
        }

    def build_db_review_prompt(self, changes: dict) -> str:
        return DB_REVIEW_PROMPT.format(
            changed_files=", ".join(changes["changed_files"]),
            diff_content=changes["diff_content"],
        )
