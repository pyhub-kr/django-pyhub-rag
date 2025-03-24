# CLI 지원 명령

## pyhub.llm

### pyhub.llm ask 명령

``` title="LLM에게 질의" hl_lines="1"
$ pyhub.llm ask "hello"
Hello! How can I assist you today?
```

``` title="멀티 턴 대화" hl_lines="1"
$ pyhub.llm ask --multi "hello"
Human: hello
AI: Hello! How can I assist you today?
Human: My name is Chinseok.
AI: Nice to meet you, Chinseok! How can I help you today?
Human: What is my name?
AI: Your name is Chinseok. How can I assist you further?
Human:
```

``` title="모델 변경" hl_lines="1"
$ pyhub.llm ask --vendor google --model gemini-2.0-flash "hello"
Hello! How can I help you today?
```

``` title="파이프를 통한 context 전달" hl_lines="1"
$ echo "Reply in Korean" | pyhub.llm ask "hello"
안녕하세요! 어떻게 도와드릴까요?
```

더 많은 옵션은 `pyhub.llm ask --help` 명령으로 확인하세요.

### pyhub.llm describe 명령

![](./assets/pyhub-128.png)

``` title="LLM에게 이미지 설명 요청" hl_lines="1"
$ pyhub.llm describe ./pyhub-128.png

<title>Pirate-Themed Skull Logo</title>
<details>This image features a stylized skull wearing a pirate hat with the word "ASK" written on it. The skull has a fierce expression, and there are two serpentine shapes in blue and yellow behind it, adding to the pirate theme.</details>
<entities>Skull, pirate hat, serpents, text ("ASK").</entities>
<hypothetical_questions>What could the "ASK" signify in the context of this logo? How might this logo be used in branding or marketing? What themes or messages does this pirate imagery convey to the audience?</hypothetical_questions>
```

+ `~/.pyhub.toml` 파일이 없다면, 라이브러리 내의 `prompts/describe/image/system.md` 파일과 `prompts/describe/image/user.md` 파일을 프롬프트로 활용합니다.
+ `~/.pyhub.toml` 파일이 있다면, 이 파일의 `prompt_templates.describe_image` 프롬프트를 활용합니다. `~/.pyhub.toml` 파일이 없다면 `pyhub toml --create` 명령으로 생성하실 수 있습니다. 

더 많은 옵션은 `pyhub.llm describe --help` 명령으로 확인하세요.

### pyhub.llm embed

LLM에게 임베딩 요청

#### fill-jsonl 명령

JSONL 파일 데이터의 각 Document마다 page_content 필드 값을 임베딩하고 embedding 필드에 저장합니다.
입력 jsonl 파일 내용을 변경하지 않고, 출력 파일을 새롭게 생성합니다.

`pyhub.parser upstage` 명령을 통해 생성된 `jsonl` 파일에 각 Document마다 임베딩 값을 채워넣을 때 유용합니다.

!!! note

    이미 embedding 필드가 있는 Document는 기존 값을 유지합니다.

``` hl_lines="1"
$ pyhub.llm embed fill-jsonl --embedding-model text-embedding-3-small ./output/argus-bitumen.jsonl
output/argus-bitumen.jsonl 파싱 중 ...
진행률: 100.0% (3/3) - 토큰: 3712

임베딩 완료!
출력 파일 생성됨: output/argus-bitumen-out.jsonl
총 항목 수: 3
총 토큰 수: 3712
```

## pyhub.rag

### pyhub.rag sqlite-vec

#### check 명령

sqlite-vec 확장이 제대로 로드될 수 있는지 확인합니다. 대개의 윈도우 배포판에서는 sqlite 확장을 모두 지원하며,
맥/리눅스에서는 sqlite 확장을 지원하도록 파이썬 재설치가 필요할 수 있습니다.
이에 대해서는 [sqlite-vec](https://ai.pyhub.kr/setup/vector-stores/sqlite-vec) 설치 가이드를 참고해주세요.

``` hl_lines="1"
$ pyhub.rag sqlite-vec check
/Users/allieus/Work/django-pyhub-rag/.venv/bin/python3 은 sqlite3 확장을 지원합니다.
sqlite-vec 확장이 정상적으로 작동합니다.
```

#### create-table 명령

SQLite 데이터베이스에 sqlite-vec 확장을 사용하여 벡터 테이블을 생성합니다. 디폴트로 `db.sqlite3` 경로에 `documents` 테이블에
`page_content`, `metadata`, `embedding` 컬럼을 생성합니다.

``` hl_lines="1"
❯ pyhub.rag sqlite-vec create-table
'documents' 가상 테이블을 db.sqlite3에 성공적으로 생성했습니다.
```

더 많은 옵션은 `pyhub.rag sqlite-vec create-table --help` 명령으로 확인하세요.

#### import-jsonl 명령

JSONL 파일의 문서 데이터를 SQLite 데이터베이스 테이블로 로드합니다. 각 문서에서 `page_content`와 `embedding` 값이 누락된 문서는 건너뜁니다.

``` hl_lines="1"
$ pyhub.rag sqlite-vec import-jsonl ./output/argus-bitumen-out.jsonl
[2025-03-23 23:29:29,897] Auto-detected table: 'documents'
[2025-03-23 23:29:29,898] Found 3 records in JSONL file
[2025-03-23 23:29:29,905] ✅ Data loading completed successfully
[2025-03-23 23:29:29,905] Inserted 3 of 3 records into table 'documents'
```

더 많은 옵션은 `pyhub.rag sqlite-vec import-jsonl --help` 명령으로 확인하세요.

#### similarity-search 명령

지정 SQLite 벡터 데이터베이스에서 의미적 유사도 검색을 수행하고, 검색어와 유사한 문서를 출력합니다.
임베딩 데이터 생성에 사용했던 임베딩 모델과 동일한 모델을 `--embedding-model` 옵션으로 지정합니다.
디폴트로 `text-embedding-3-small`입니다.

```
$ pyhub.rag sqlite-vec similarity-search "비투멘의 수출 가격"

metadata: {'id': 0, 'page': 5, 'total_pages': 21, 'category': 'header', 'api': '2.0', 'model': 'document-parse-250116', 'image_descriptions': "<image name='p005/12-chart.jpg'><title>헝가리와 루마니아의
국내 지표 비교</title>\n<details>헝가리와 루마니아의 국내 지표가 2022년 7월부터 2023년 3월까지의 기간 동안 어떻게 변화했는지를 보여주는 그래프입니다. 헝가리의 지표는 전반적으로 상승세를 보였고, 루마니아의
지표는 상대적으로 더 낮은 수준을 유지했습니다.</details>\n<entities>헝가리, 루마니아, 국내 지표, 시간(7월, 9월, 12월, 3월)</entities>\n<hypothetical_questions>1. 헝가리와 루마니아의 국내 지표 차이는 어떤
경제적 요인에 의해 발생했을까? 2. 향후 두 나라의 경제 성장률은 어떻게 변화할 가능성이 있을까? 3. 이 데이터가 정책 결정에 어떤 영향을 미칠 수 있을까?</hypothetical_questions></image>", 'source':
'argus-bitumen.pdf', 'distance': 0.7945679426193237}

Argus Bitumen (생략)
```

``` title="파이프를 통한 context 전달" hl_lines="1"
$ pyhub.rag sqlite-vec similarity-search "비투멘의 수출 가격" | pyhub.llm ask "비투멘의 수출 가격"
Naive RAG 출력 ...
```

더 많은 옵션은 `pyhub.rag sqlite-vec similarity-search --help` 명령으로 확인하세요.

## pyhub.parser

### pyhub.parser upstage 명령

업스테이지 Document Parse API를 활용하여, 한 번의 명령 만으로 PDF 파일을 파싱하고, Vector Store에 바로 저장할 수 있도록
랭체인 Document 포맷의 jsonl 파일을 생성합니다.

Document Parse API에서는 이미지도 추출해주는 데요. 보다 높은 성능의 RAG를 위해서는 이미지에 대한 설명도 미리 생성해주는 것이 좋습니다.
이때 `--enable-image-descriptor` (`-i`) 옵션을 지정하면 이미지 설명 생성까지 한 번에 수행해줍니다.

``` hl_lines="1"
$ pyhub.parser upstage --pages "1,3,5" --enable-image-descriptor ./argus-bitumen.pdf
출력 폴더 output이(가) 이미 존재합니다. 삭제 후에 재생성하시겠습니까? [y/N]: y
[2025-03-23 23:38:07,187] PDF 파일 : 총 21 페이지
[2025-03-23 23:38:07,190] 변환할 페이지 : 1, 3, 5
[2025-03-23 23:38:07,190] 1 페이지 변환
[2025-03-23 23:38:07,237] Upstage document-parse-250116 (2.0) API 요청에서 21개의 요소를 찾았습니다.
[2025-03-23 23:38:07,239] 21개의 요소에서 3개의 이미지를 찾았습니다.
[2025-03-23 23:38:07,239] openai gpt-4o-mini 모델을 통해 이미지 설명을 생성합니다.
[2025-03-23 23:38:07,239] request describe_images [1/3] : p001/13-table.jpg
[2025-03-23 23:38:07,268] request describe_images [2/3] : p001/16-chart.jpg
[2025-03-23 23:38:07,274] request describe_images [3/3] : p001/18-table.jpg
[2025-03-23 23:38:07,292] 3 페이지 변환
[2025-03-23 23:38:07,375] Upstage document-parse-250116 (2.0) API 요청에서 22개의 요소를 찾았습니다.
[2025-03-23 23:38:07,376] 22개의 요소에서 4개의 이미지를 찾았습니다.
[2025-03-23 23:38:07,376] openai gpt-4o-mini 모델을 통해 이미지 설명을 생성합니다.
[2025-03-23 23:38:07,376] request describe_images [1/4] : p003/12-chart.jpg
[2025-03-23 23:38:07,382] request describe_images [2/4] : p003/14-table.jpg
[2025-03-23 23:38:07,396] request describe_images [3/4] : p003/18-table.jpg
[2025-03-23 23:38:07,404] request describe_images [4/4] : p003/19-table.jpg
[2025-03-23 23:38:07,412] 5 페이지 변환
[2025-03-23 23:38:07,428] Upstage document-parse-250116 (2.0) API 요청에서 27개의 요소를 찾았습니다.
[2025-03-23 23:38:07,428] 27개의 요소에서 1개의 이미지를 찾았습니다.
[2025-03-23 23:38:07,428] openai gpt-4o-mini 모델을 통해 이미지 설명을 생성합니다.
[2025-03-23 23:38:07,428] request describe_images [1/1] : p005/12-chart.jpg
성공: output/argus-bitumen.jsonl 경로에 3개의 Document를 jsonl 포맷으로 생성했습니다.
성공: output/argus-bitumen.md 경로에 통합 문서를 생성했습니다.
성공: output/argus-bitumen.html 경로에 통합 문서를 생성했습니다.
성공: output/argus-bitumen.txt 경로에 통합 문서를 생성했습니다.
```

[명령 한 방에 PDF 변환하기](./parser/upstage-document-parse/index) 문서를 참고하세요.

더 많은 옵션은 `pyhub.parser upstage --help` 명령으로 확인하세요.

!!! tip

    이미지 설명은 `page_content`가 아닌 `metadata`의 `image_descriptions`에 저장되어있습니다.
    임베딩은 대개 `page_content` 값만 하는 데요. 필요하다면 `metadata["image_descriptions"]` 값을 `page_content`에 반영한 후에
    임베딩을 생성하실 수도 있습니다.