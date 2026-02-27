# Branch Protection Setup

## 목적
- `main` 브랜치에 최소 머지 게이트를 강제하여 병렬 개발 충돌/회귀를 줄입니다.

## 적용 규칙
- Pull request 필수
- 최소 1명 승인 필수
- CODEOWNERS 리뷰 필수
- 오래된 승인 무효화(dismiss stale reviews)
- 마지막 push 후 재승인(require last push approval)
- Conversation resolution 필수
- Force push / branch delete 금지
- Linear history 강제
- Required checks:
  - `CI / lint`
  - `Public Repo Guard / guard`

## 방법 A (권장): 자동 적용 스크립트
1. GitHub PAT 준비 (repo admin 권한)
2. 로컬에서 실행:

```bash
cd /Users/isanginn/Workspace/Agent_Workspace
export GITHUB_TOKEN="<github_pat_with_admin_rights>"
bash scripts/security/apply-branch-protection.sh
```

기본 타깃:
- owner: `Merchantlee99`
- repo: `Personal-AI-agent`
- branch: `main`

다른 저장소에 적용하려면:

```bash
REPO_OWNER="your-owner" REPO_NAME="your-repo" TARGET_BRANCH="main" \
GITHUB_TOKEN="<token>" \
bash scripts/security/apply-branch-protection.sh
```

## 방법 B: 수동 UI 적용
1. GitHub Repository Settings -> Branches
2. Add branch protection rule (`main`)
3. 아래 옵션 활성화:
- Require a pull request before merging
- Require approvals: 1
- Require review from Code Owners
- Dismiss stale pull request approvals
- Require approval of the most recent reviewable push
- Require conversation resolution before merging
- Require status checks to pass before merging
  - `CI / lint`
  - `Public Repo Guard / guard`
- Do not allow bypassing the above settings
- Do not allow force pushes
- Do not allow deletions

## 검증
- 보호 규칙 조회:

```bash
curl -sS -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/Merchantlee99/Personal-AI-agent/branches/main/protection" \
  | head -n 40
```

정상 적용 시 `required_status_checks`, `required_pull_request_reviews` 항목이 표시됩니다.
