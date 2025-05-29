"""TOML 관련 공통 유틸리티 함수들"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional, List

from rich.console import Console

console = Console()


def get_default_toml_content() -> str:
    """기본 TOML 설정 내용을 반환합니다."""
    from pathlib import Path
    
    # 실제 프롬프트 템플릿 로드
    prompt_base = Path(__file__).parent.parent.parent / "parser" / "templates" / "prompts" / "describe"
    
    # 이미지 설명 프롬프트
    image_system_prompt = ""
    image_user_prompt = ""
    image_system_path = prompt_base / "image" / "system.md"
    image_user_path = prompt_base / "image" / "user.md"
    
    if image_system_path.exists():
        image_system_prompt = image_system_path.read_text(encoding="utf-8").strip()
    if image_user_path.exists():
        image_user_prompt = image_user_path.read_text(encoding="utf-8").strip()
    
    # 테이블 설명 프롬프트
    table_system_prompt = ""
    table_user_prompt = ""
    table_system_path = prompt_base / "table" / "system.md"
    table_user_path = prompt_base / "table" / "user.md"
    
    if table_system_path.exists():
        table_system_prompt = table_system_path.read_text(encoding="utf-8").strip()
    if table_user_path.exists():
        table_user_prompt = table_user_path.read_text(encoding="utf-8").strip()
    
    return f'''[env]
# API Keys
UPSTAGE_API_KEY = ""
OPENAI_API_KEY = ""
ANTHROPIC_API_KEY = ""
GOOGLE_API_KEY = ""

# Database
DATABASE_URL = ""

# Optional
TOML_PATH = ""
ENV_PATH = ""

[rag]
# RAG (Retrieval Augmented Generation) 설정
# 기본 벡터 스토어 백엔드 선택 (pgvector, sqlite-vec)
default_backend = "sqlite-vec"

[rag.backends.pgvector]
# PostgreSQL pgvector 벡터 데이터베이스 설정
enabled = true
# database_url = "postgresql://user:password@localhost:5432/vectordb"
# default_table = "documents"
# default_dimensions = 1536
# index_type = "hnsw"  # 옵션: hnsw, ivfflat
# distance_metric = "cosine"  # 옵션: cosine, l2, inner_product

[rag.backends.sqlite-vec]
# SQLite-vec 벡터 데이터베이스 설정
enabled = true
# db_path = "~/.pyhub/vector.db"
# default_table = "documents"
# default_dimensions = 1536
# distance_metric = "cosine"  # 옵션: cosine, l2

[mcp]
# MCP (Model Context Protocol) 서버 설정
# 여러 MCP 서버를 정의할 수 있습니다

# [mcp.servers.math]
# # 수학 도구를 제공하는 MCP 서버 예제
# command = "python"
# args = ["/path/to/math_server.py"]
# # env = { PYTHONPATH = "/custom/path" }  # 선택적: 환경 변수
# # filter_tools = ["add", "multiply"]  # 선택적: 특정 도구만 로드

# [mcp.servers.web]
# # 웹 검색 도구를 제공하는 MCP 서버 예제
# command = "node"
# args = ["/path/to/web_search_server.js"]
# # filter_tools = ["search", "browse"]

[prompt_templates.describe_image]
system = """{image_system_prompt}"""
user = """{image_user_prompt}"""

[prompt_templates.describe_table]
system = """{table_system_prompt}"""
user = """{table_user_prompt}"""

[prompt_templates.custom_template]
system = "당신은 유용한 AI 어시스턴트입니다."
user = "{{query}}"

[cache]
default_timeout = 2592000  # 30 days
max_entries = 5000
'''


def get_editors_for_platform() -> List[str]:
    """플랫폼별 편집기 목록을 반환합니다."""
    if sys.platform.startswith("win"):
        return ["code", "notepad++", "notepad"]
    else:
        return ["code", "vim", "nano", "emacs", "gedit"]


def open_file_with_editor(file_path: Path) -> bool:
    """
    파일을 편집기로 엽니다.
    
    Args:
        file_path: 열 파일 경로
        
    Returns:
        성공 여부
    """
    # 1. 환경변수에서 에디터 확인
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR")
    
    # 2. 플랫폼별 기본 명령 시도
    if not editor:
        if sys.platform.startswith("win"):
            # Windows
            try:
                subprocess.run(["start", str(file_path)], shell=True, check=True)
                console.print(f"[green]✓ Windows 기본 프로그램으로 파일을 열었습니다.[/green]")
                return True
            except subprocess.CalledProcessError:
                pass
        elif sys.platform.startswith("darwin"):
            # macOS
            try:
                subprocess.run(["open", str(file_path)], check=True)
                console.print(f"[green]✓ macOS 기본 프로그램으로 파일을 열었습니다.[/green]")
                return True
            except subprocess.CalledProcessError:
                pass
        else:
            # Linux
            try:
                subprocess.run(["xdg-open", str(file_path)], check=True)
                console.print(f"[green]✓ 기본 프로그램으로 파일을 열었습니다.[/green]")
                return True
            except subprocess.CalledProcessError:
                pass
    
    # 3. 에디터 명령으로 시도
    if editor:
        editors = [editor]
    else:
        editors = get_editors_for_platform()
    
    for ed in editors:
        try:
            # Windows에서 notepad의 경우 특별 처리
            if sys.platform.startswith("win") and ed == "notepad":
                # notepad는 항상 존재하므로 직접 실행
                subprocess.run([ed, str(file_path)], check=True)
            else:
                # 다른 에디터들은 일반적인 방식으로 시도
                subprocess.run([ed, str(file_path)], check=True, 
                             stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            console.print(f"[green]✓ {ed} 에디터로 파일을 열었습니다.[/green]")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
    
    # 모든 시도가 실패한 경우
    console.print(f"[red]오류: 파일을 열 수 있는 에디터를 찾을 수 없습니다.[/red]")
    console.print(f"[dim]시도한 에디터: {', '.join(editors)}[/dim]")
    console.print(f"[dim]VISUAL 또는 EDITOR 환경변수를 설정하거나, 다음 명령으로 파일 내용을 확인하세요:[/dim]")
    console.print(f"  [cyan]pyhub toml show[/cyan]")
    return False