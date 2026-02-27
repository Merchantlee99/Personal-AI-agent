# NanoClaw 운영 플레이북 (2계층 인덱스)

기준 경로: `/Users/isanginn/Workspace/Agent_Workspace`

## 목적

운영 절차를 공개용/비공개용으로 분리해,

- 저장소 공유 문서에는 운영 표준만 남기고
- 실제 민감 대응 절차(계정/복구/로컬 오퍼레이션 상세)는 로컬 전용 문서로 관리합니다.

## 계층 구조

1. 공개 계층 (Git tracked)
   - 파일: `/Users/isanginn/Workspace/Agent_Workspace/docs/OPERATIONS_PLAYBOOK_PUBLIC.md`
   - 용도:
     - 운영 표준 절차
     - 장애 등급(SLA)
     - 일반 점검 체크리스트
     - 공용 런북(민감값 미포함)

2. 비공개 계층 (Git ignored)
   - 파일: `/Users/isanginn/Workspace/Agent_Workspace/ops_private/OPERATIONS_PLAYBOOK_PRIVATE.md`
   - 용도:
     - 실제 운영 담당자 대응 절차
     - 계정/토큰 복구 실무 템플릿
     - 비상 대응 체크리스트(내부 메모)
   - Git 업로드 금지: `.gitignore`에서 `/ops_private/*` 차단

## 초기 생성 절차 (1회)

```bash
cd /Users/isanginn/Workspace/Agent_Workspace
cp docs/OPERATIONS_PLAYBOOK_PRIVATE_TEMPLATE.md ops_private/OPERATIONS_PLAYBOOK_PRIVATE.md
```

생성 후 `ops_private/OPERATIONS_PLAYBOOK_PRIVATE.md`에 실제 운영자 메모를 채워서 사용합니다.

## 운영 원칙

- 공개 문서에는 비밀값/개인 식별 정보/직접 접근 절차를 쓰지 않습니다.
- 비공개 문서는 로컬에서만 유지하고, 스크린샷 공유 시에도 내용 마스킹합니다.
- 절차 변경 시:
  1) 공개 문서(`...PUBLIC.md`) 업데이트
  2) 비공개 문서(`ops_private/...`) 동기화
  3) 변경 이력은 `/Users/isanginn/Workspace/Agent_Workspace/docs/MEMORY.md`에 누적
