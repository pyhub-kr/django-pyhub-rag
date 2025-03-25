# TOML 설정 파일

`pyhub.parser upstage` 명령을 비롯한 모든 `pyhub` CLI 명령에서는 설정파일로서
디폴트로 `~/.pyhub.toml` 경로를 사용하며 `--toml-path` 인자로 로딩할 위치를 직접 지정하실 수 있습니다.

## 설정 파일 구조

+ `[env]` : 환경변수
+ `[prompt_templates.describe_image]` : 이미지 설명 요청, 시스템/유저 프롬프트
+ `[prompt_templates.describe_table]` : 테이블 이미지 설명 요청, 시스템/유저 프롬프트

``` toml
[env]
UPSTAGE_API_KEY = "up_xxxxx..."
OPENAI_API_KEY = "sk-xxxxx..."
# ANTHROPIC_API_KEY = "sk-ant-xxxxx..."
# GOOGLE_API_KEY = "AIxxxxx...."
# VECTORSTORE_DATABASE_URL = "postgresql://postgres:pw@localhost:5432/postgres"

[prompt_templates.describe_image]
system = """..."""

user = """..."""

[prompt_templates.describe_table]
system = """..."""

user = """..."""
```

!!! tip

    `toml` 파일에서는 #` 으로 시작하는 줄은 주석으로서 무시됩니다.

!!! note

    프롬프트 문자열은 Format String 문법과

    ```
    검색어 : {query}
    ```

    장고 템플릿 엔진 문법을 지원합니다. `{% for %}{% endfor %}`, `{% if %}{% endif %}` 템플릿 태그도 사용하실 수 있습니다.

    ```
    검색어 : {{ query }}
    ```

## 설정 파일 생성하기

`pyhub toml --create` 명령을 활용하시면, `~/.pyhub.toml` 경로에 파일을 자동으로 생성해줍니다. 

```
pyhub toml --create
```

## `~/.pyhub.env` 파일을 사용하실 경우

모든 CLI에서는 다음 순서로 환경변수를 로딩합니다.

1. `~/.pyhub.toml`의 `[env]` 항목
2. `~/.pyhub.env`

두 파일에서 같은 이름의 환경변수 설정이 있을 경우, 나중의 환경변수 설정이 앞의 환경변수 설정을 덮어씁니다.