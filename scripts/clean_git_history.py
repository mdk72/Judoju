#!/usr/bin/env python
"""
Git 히스토리에서 .env.example의 민감정보를 제거하는 스크립트
"""
import subprocess
import sys

def run_command(cmd):
    """명령어 실행"""
    print(f"실행: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8')
    print(result.stdout)
    if result.returncode != 0:
        print(f"에러: {result.stderr}", file=sys.stderr)
    return result.returncode == 0

def main():
    """메인 함수"""
    print("=" * 60)
    print("Git 히스토리 민감정보 제거 스크립트")
    print("=" * 60)
    
    # 1. 현재 상태 백업
    print("\n[1단계] 현재 상태 백업...")
    run_command("git branch backup-before-clean")
    
    # 2. 문제 커밋을 interactive rebase로 수정
    print("\n[2단계] 문제 커밋 수정 준비...")
    print("커밋 c45715c에서 민감정보를 제거해야 합니다.")
    print("\n수동 작업 필요:")
    print("1. git rebase -i c45715c~1")
    print("2. 해당 커밋 앞에서 'edit'으로 변경")
    print("3. .env.example 파일을 안전한 내용으로 수정 후:")
    print("   git add .env.example")
    print("   git commit --amend --no-edit")
    print("   git rebase --continue")
    print("4. git push origin main --force")
    
    print("\n또는 BFG Repo-Cleaner 사용:")
    print("java -jar bfg.jar --replace-text passwords.txt <저장소 경로>")

if __name__ == "__main__":
    main()
