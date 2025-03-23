# 이미지 설명 요청 프롬프트

`pyhub.parser upstage` 명령에서는 아래 4개의 프롬프트를 사용합니다.

+ 이미지 설명 요청 프롬프트
    - [`prompts/describe/image/system.md`](https://github.com/pyhub-kr/django-pyhub-rag/blob/main/src/pyhub/parser/templates/prompts/describe/image/system.md?plain=1)
    - [`prompts/describe/image/user.md`](https://github.com/pyhub-kr/django-pyhub-rag/blob/main/src/pyhub/parser/templates/prompts/describe/image/user.md?plain=1)
+ 테이블 이미지 설명 요청 프롬프트
    - [`prompts/describe/table/system.md`](https://github.com/pyhub-kr/django-pyhub-rag/blob/main/src/pyhub/parser/templates/prompts/describe/table/system.md?plain=1)
    - [`prompts/describe/table/user.md`](https://github.com/pyhub-kr/django-pyhub-rag/blob/main/src/pyhub/parser/templates/prompts/describe/table/user.md?plain=1)

## 커스텀 프롬프트

`pyhub.parser upstage` 명령에서는 `--toml-path` 인자를 통해 TOML 설정 파일을 지원합니다.

[TOML 설정 파일](../../toml) 문서를 참고해서, 설정파일을 통해 커스텀 프롬프트를 설정하실 수 있습니다.