import logging
from github import Github

logger = logging.getLogger(__name__)

BOT_MARKER = "<!-- ai-reviewer-bot -->"


class GitHubClient:
    def __init__(self, token: str):
        self._gh = Github(token)

    def get_pr_diff(self, repo_name: str, pr_number: int) -> tuple[str, list[str]]:
        repo = self._gh.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        files = list(pr.get_files())
        file_names = [f.filename for f in files]
        diff_parts = []
        for f in files:
            diff_parts.append(f"+++ b/{f.filename}")
            if f.patch:
                diff_parts.append(f.patch)
        return "\n".join(diff_parts), file_names

    def get_issue_body(self, repo_name: str, issue_number: int) -> tuple[str, str]:
        repo = self._gh.get_repo(repo_name)
        issue = repo.get_issue(issue_number)
        return issue.title, issue.body or ""

    def post_pr_comment(self, repo_name: str, pr_number: int, body: str) -> None:
        repo = self._gh.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        marked_body = f"{BOT_MARKER}\n{body}"
        for comment in pr.get_issue_comments():
            if BOT_MARKER in comment.body:
                comment.edit(marked_body)
                logger.info("PR #%d 기존 봇 댓글 업데이트", pr_number)
                return
        pr.create_issue_comment(marked_body)
        logger.info("PR #%d 새 댓글 작성", pr_number)

    def post_issue_comment(self, repo_name: str, issue_number: int, body: str) -> None:
        repo = self._gh.get_repo(repo_name)
        issue = repo.get_issue(issue_number)
        marked_body = f"{BOT_MARKER}\n{body}"
        for comment in issue.get_comments():
            if BOT_MARKER in comment.body:
                comment.edit(marked_body)
                logger.info("이슈 #%d 기존 봇 댓글 업데이트", issue_number)
                return
        issue.create_comment(marked_body)
        logger.info("이슈 #%d 새 댓글 작성", issue_number)
