# 생성된 데이터로 Simple RAG

앞선 페이지에서
[argus-bitumen.pdf](https://www.argusmedia.com/-/media/project/argusmedia/mainsite/english/documents-and-files/sample-reports/argus-bitumen.pdf?rev=7512cf07937e4e4cbb8889c87780edf7) 파일을 파싱하여,
[jsonl 등의 다양한 파일들](https://github.com/pyhub-kr/django-pyhub-rag/tree/main/samples/argus-bitumen)을 생성했습니다.

## jsonl 포맷 살펴보기

그 파일들 중에 `argus-bitumen.jsonl` 파일에는 각 줄 마다 랭체인 Document 포맷의 문서가 저장되어있습니다.

+ `page_content` 항목에는 문자열 타입으로서 텍스트 내용이 저장
+ `metadata` 항목에는 `{"id": 0, "page": 2, "total_pages": 21, "category": "header", "api": "2.0", "model": "document-parse-250116", "image_descriptions": "이미지 설명"}` 처럼 문서의 메타 정보가 저장되어있습니다.

``` jsonl title="argus-bitumen.jsonl 파일 중 1줄"
{"page_content": "Ⓡ\n\n# argus\n\n# Argus Bitumen\n\nEurope, Africa, Middle East and Asia-Pacific prices and commentary\nIncorporating Argus Asphalt Report\n\nargusmedia.com\n\nIssue 24-12 I Friday 22 March 2024\n\nSUMMARY\n\nBitumen prices rose across much of Europe, as supply\ntightened in the north and fuel oil values firmed, while in\nAsia weak demand continued to weigh on the market, with\nSingapore and South Korean prices both down on the week.\n\nDisruptions at two French refineries continued to\nsqueeze bitumen supply in northwest Europe, helping to\npush up Rotterdam and Baltic cargo differentials to fob Rot-\nterdam high-sulphur fuel oil (HSFO) barges.\n\nMediterranean bitumen market activity and demand lev-\nels were starting to rise with warmer weather in many Euro-\npean markets, a factor that along with rising regional HSFO\nprices, pushed up domestic truck prices in some markets.\n\nPrice levels in most sub-Saharan African markets were\nbroadly stable, although cargo values into west African ter-\nminals rose sharply, while there were some freight rate falls\nfor container shipping movements into east Africa.\n\nSingapore bitumen prices edged lower, as the southeast\nAsian market continued to see a lack of demand outlets,\nwith only limited buyers seeking out April-loading cargoes.\nSeveral oil majors were still holding on to unsold April-load-\ning volumes and some emerged on the Argus Open Markets\n(AOM) platform to seek out buyers.\n\nPRICES\n\n| Bitumen prices at key locations, 16-22 Mar | Bitumen prices at key locations, 16-22 Mar | Bitumen prices at key locations, 16-22 Mar | Bitumen prices at key locations, 16-22 Mar | $/t ± |\n| --- | --- | --- | --- | --- |\n|  |  | Low | High | $/t ± |\n| Export cargo prices fob | Export cargo prices fob |  |  |  |\n| Mediterranean |  | 445.43 | 449.77 | +29.05 |\n| Rotterdam |  | 482.15 | 487.15 | +26.00 |\n| Baltic |  | 470.15 | 474.15 | +26.00 |\n| Singapore |  | 383.00 | 408.60 | -6.70 |\n| South Korea |  | 400.00 | 407.00 | -5.00 |\n| Mideast Gulf |  | 283.50 | 380.00 | +9.75 |\n| Delivered cargo prices cfr | Delivered cargo prices cfr |  |  |  |\n| North Africa | Alexandria, bulk | 491.00 | 501.00 | +32.00 |\n| East Africa | Mombasa, drum | 430.00 | 440.00 | +2.00 |\n| West Africa | Lagos, bulk | 633.00 | 643.00 | +29.00 |\n| East China coast |  | 435.00 | 450.00 | +5.00 |\n| Domestic prices |  |  |  |  |\n| Antwerp | ex-works | 576 | 587 | +2.00 |\n| Southern Germany | ex-works | 522 | 533 | -3.00 |\n| Hungary | ex-works | 571 | 582 | -3.00 |\n| Italy | ex-works inc tax | 549 | 560 | +8.00 |\n| Indonesia | ex-works | 587.00 | 587.00 | -3.00 |\n| Mumbai | bulk | 499.00 | 502.00 | -8.50 |\n\n\nNorth Sea Dated VS Rotterdam domestic\n\n$/bl\n\n![image](chart/16.jpg)\n- Chart Type: line\n|  | Jul 7 | Jul 29 | Sep 29 | Dec 22 | Mar 22 | North Sea Dated 10 | Rotterdam domestic |\n| --- | --- | --- | --- | --- | --- | --- | --- |\n| item_01 | 80% | 90% | 100% | 80% | 90% | 85% | 90% |\n\n\nCONTENTS\n\n| Key bitumen prices | 1 |\n| --- | --- |\n| Map of waterborne bitumen prices | 2 |\n| Northwest and central Europe | 3-5 |\n| Mediterranean | 6-8 |\n| Sub-Saharan Africa | 9-11 |\n| Asia-Pacific and Middle East | 12-16 |\n| Vessel tracking indications | 17 |\n| Bitumen news | 18-20 |\n", "metadata": {"id": 0, "page": 1, "total_pages": 21, "category": "paragraph", "api": "2.0", "model": "document-parse-250116", "image_descriptions": "<image name='table/13.jpg'><title>\n비투멘 가격 현황 (2023년 3월 16-22일)\n</title>\n<details>\n이 표는 비투멘의 수출 및 국내 가격을 나타냅니다. 수출 화물 가격은 지중해에서 $445.43에서 $449.77로, 로테르담에서 $482.15에서 $487.15로 변동했습니다. 국내 가격은 앤트워프에서 $576에서 $587로, 남부 독일에서 $522에서 $523로 보고되었습니다.\n</details>\n<entities>\n비투멘, 수출 화물 가격, 국내 가격, 지중해, 로테르담, 앤트워프, 남부 독일, 동아시아 해안\n</entities>\n<hypothetical_questions>\n- 비투멘 가격 상승이 건설 산업에 미치는 영향은 무엇인가요?\n- 향후 몇 달 동안 비투멘 가격이 어떻게 변동할 가능성이 있나요?\n</hypothetical_questions></image>\n\n<image name='chart/16.jpg'><title>북해 및 로테르담 국내 가격 추세</title>\n<details>이 그래프는 7월부터 3월까지의 북해 가격과 로테르담 국내 가격의 변화를 보여줍니다. 북해 가격은 전반적으로 상승세를 보였으며, 로테르담 가격은 상대적으로 안정적인 흐름을 유지했습니다.</details>\n<entities>북해, 로테르담, 가격 추세</entities>\n<hypothetical_questions>1. 북해 가격 상승의 주요 원인은 무엇일까요? 2. 로테르담 가격이 안정적인 이유는 무엇일까요? 3. 향후 가격 변동이 시장에 미치는 영향은 어떻게 될까요?</hypothetical_questions></image>\n\n<image name='table/18.jpg'><title>\n비투멘 가격 및 관련 정보\n</title>\n<details>\n이 표는 비투멘 가격 및 관련 정보를 요약하고 있습니다. 주요 항목은 다음과 같습니다: \n- 비투멘 가격: 1페이지\n- 수륙 비투멘 가격 지도: 2페이지\n- 북서 및 중앙 유럽: 3-5페이지\n- 지중해: 6-8페이지\n- 사하라 이남 아프리카: 9-11페이지\n- 아시아-태평양 및 중동: 12-16페이지\n- 선박 추적 정보: 17페이지\n- 비투멘 뉴스: 18-20페이지\n</details>\n<entities>\n비투멘 가격, 수륙 비투멘 가격, 북서 유럽, 중앙 유럽, 지중해, 사하라 이남 아프리카, 아시아-태평양, 중동, 선박 추적, 비투멘 뉴스\n</entities>\n<hypothetical_questions>\n- 비투멘 가격의 변화가 각 지역의 시장에 미치는 영향은 무엇일까요?\n- 수륙 비투멘 가격 지도가 향후 비투멘 수출에 어떤 역할을 할까요?\n</hypothetical_questions></image>"}}
```

`argus-bitumen.jsonl` 파일을 읽으실 때에는 다음과 같이 line by line 단위로 JSON 파싱하여 객체화하여 Vector Store에 저장하시면 됩니다.

``` python
import json

for line in open("argus-bitumen.jsonl"):
    doc = json.loads(line)
    doc["page_content"]  # str 타입
    doc["metadata"]  # dict 타입
```

## Vector Store에 저장하고, 유사 문서 검색하기

faiss는 Facebook AI Research에서 C++로 개발했으며 파이썬 바인딩을 지원합니다.

FAISS는 기본적으로 벡터 색인(index)만 저장합니다. 즉, 원본 데이터(문서 정보, 메타데이터)는 저장되지 않으며 따로 관리해주어야만,
검색 결과에서 원본 데이터를 참조할 수 있습니다.

=== "faiss 직접 활용"

    라이브러리 설치

    ```
    pip install -U faiss-cpu openai numpy
    ```

    ``` py linenums="1"
    import json
    from pathlib import Path
    
    import faiss
    import numpy as np
    import openai
    
    
    def get_embedding(s: str) -> np.ndarray:
        """문자열을 OpenAI Embedding API를 통해 벡터로 변환하여 반환합니다."""
        print("try embedding for", repr(s)[:40], "...")
        response = openai.embeddings.create(input=s, model="text-embedding-3-small")
        return np.array(response.data[0].embedding, dtype=np.float32)
    
    
    def load_documents() -> list[dict]:
        """argus-bitumen.jsonl 파일을 읽어 문서 리스트로 반환합니다."""
    
        documents = []
    
        for line in open("argus-bitumen.jsonl"):
            doc = json.loads(line)
            page_content = doc["page_content"]
            metadata = doc["metadata"]
            documents.append({"page_content": page_content, "metadata": metadata})

        return documents
    
    
    def create_if_not_exist(index_file_path: Path) -> None:
        """문서 임베딩을 생성하고 FAISS 색인을 지정된 경로에 저장합니다.
    
        이미 색인 파일이 존재하는 경우 생성 과정을 건너뜁니다.
        """
    
        if index_file_path.exists():
            print("index already exists")
        else:
            print("creating index")
            documents = load_documents()
            embeddings = [get_embedding(doc["page_content"]) for doc in documents]
    
            # 벡터를 FAISS 색인에 저장
            dimensions: int = len(embeddings[0])  # 벡터 차원
            index = faiss.IndexFlatL2(dimensions)  # 임베딩 차원의 Vector Store 생성
            index.add(np.array(embeddings))  # Vector Store에 임베딩 데이터 저장
            faiss.write_index(index, str(index_file_path))
            print("created", index_file_path)
    
    
    def search(index_file_path, query: str) -> list[tuple[int, dict]]:
        """쿼리와 의미적으로 유사한 문서를 FAISS 색인에서 검색하여 반환합니다.
    
        검색 결과로 문서 인덱스와 해당 문서 정보를 포함한 튜플 리스트를 반환합니다.
        """
    
        index = faiss.read_index(str(index_file_path))
        query_embedding = get_embedding(query).reshape(1, -1)
    
        # D: 각 검색 결과의 거리(Distance) 값 배열 - 값이 작을수록 유사도가 높음
        # I: 각 검색 결과의 인덱스(Index) 값 배열 - 원본 문서 배열에서의 위치
        D, I = index.search(query_embedding, 4)  # Top 4 검색
    
        documents = load_documents()
    
        doc_list = []
        for document_index in I[0]:
            doc_list.append((document_index, documents[document_index]))
    
        return doc_list
    
    
    def main():
        """FAISS 색인을 생성하고 비트멘 가격 트렌드에 관한 문서를 검색합니다.
    
        색인 파일이 존재하지 않으면 새로 생성하고, 존재하면 기존 색인을 사용합니다.
        검색 결과로 찾은 문서의 인덱스와 내용 일부를 출력합니다.
        """
        index_file_path = Path("faiss_index.bin")
    
        create_if_not_exist(index_file_path)
    
        doc_list = search(index_file_path, "비트멘 가격 트렌드")
        for idx, doc in doc_list:
            print(idx, repr(doc["page_content"])[:40], "...")
    
    
    if __name__ == "__main__":
        main()
    ```

    ??? 실행결과

        ```
        creating index
        try embedding for 'Ⓡ\n\n# argus\n\n# Argus Bitumen\n\nEuro ...
        try embedding for 'Argus Bitumen\n\nIssue 24-12  Friday 22 ...
        try embedding for "Argus Bitumen\n\nIssue 24-12  Friday 22 ...
        try embedding for 'Argus Bitumen\n\nIssue 24-12  Friday 22 ...
        try embedding for "Argus Bitumen\n\nIssue 24-12  Friday 22 ...
        try embedding for "Argus Bitumen\n\nIssue 24-12  Friday 22 ...
        try embedding for "Argus Bitumen\n\nIssue 24-12  Friday 22 ...
        try embedding for "Argus Bitumen\n\nIssue 24-12  Friday 22 ...
        try embedding for "Argus Bitumen\n\nIssue 24-12  Friday 22 ...
        try embedding for "Argus Bitumen\n\nIssue 24-12  Friday 22 ...
        try embedding for 'Argus Bitumen\n\nIssue 24-12  Friday 22 ...
        try embedding for "Argus Bitumen\n\nIssue 24-12  Friday 22 ...
        try embedding for "Argus Bitumen\n\nIssue 24-12  Friday 22 ...
        try embedding for "Argus Bitumen\n\nIssue 24-12  Friday 22 ...
        try embedding for "Argus Bitumen\n\nIssue 24-12  Friday 22 ...
        try embedding for 'Argus Bitumen\n\nIssue 24-12  Friday 22 ...
        try embedding for "Argus Bitumen\n\nIssue 24-12  Friday 22 ...
        try embedding for 'Argus Bitumen\n\nIssue 24-12  Friday 22 ...
        try embedding for 'Argus Bitumen\n\nIssue 24-12  Friday 22 ...
        try embedding for 'Argus Bitumen\n\nIssue 24-12  Friday 22 ...
        try embedding for 'Argus Bitumen\n\nIssue 24-12 I Friday 2 ...
        created faiss_index.bin
        try embedding for '비트멘 가격 트렌드' ...
        1 'Argus Bitumen\n\nIssue 24-12  Friday 22 ...
        0 'Ⓡ\n\n# argus\n\n# Argus Bitumen\n\nEuro ...
        2 "Argus Bitumen\n\nIssue 24-12  Friday 22 ...
        15 'Argus Bitumen\n\nIssue 24-12  Friday 22 ...
        ```
    
        다시 실행해보면 이렇게 기존의 `faiss_index.bin` 파일을 다시 로딩합니다.
    
        ```
        index already exists
        try embedding for '비트멘 가격 트렌드' ...
        1 'Argus Bitumen\n\nIssue 24-12  Friday 22 ...
        0 'Ⓡ\n\n# argus\n\n# Argus Bitumen\n\nEuro ...
        2 "Argus Bitumen\n\nIssue 24-12  Friday 22 ...
        15 'Argus Bitumen\n\nIssue 24-12  Friday 22 ...
        ```

=== "랭체인 통해서 faiss 활용"

    랭체인에서는 `langchain-community` 라이브러리의 `FAISS`를 활용하며,
    앞서 생성된 `faiss.write_index(...)`과는 다른 저장 체계를 가집니다.

    라이브러리 설치

    ```
    pip install -U langchain langchain-openai faiss-cpu openai
    ```

    ``` py linenums="1"
    import json
    from pathlib import Path
    
    from langchain.schema import Document
    from langchain_community.vectorstores import FAISS
    from langchain_openai import OpenAIEmbeddings

    def load_documents() -> list[Document]:
        documents = []
    
        for line in open("argus-bitumen.jsonl"):
            doc = json.loads(line)
            page_content = doc["page_content"]
            metadata = doc["metadata"]
            documents.append(Document(page_content=page_content, metadata=metadata))
    
        return documents

    def create_if_not_exist(index_folder_path: Path) -> FAISS:
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    
        if index_folder_path.exists() is False:
            print("creating new index...")
            documents = load_documents()
            vectorstore = FAISS.from_documents(documents, embeddings)
            vectorstore.save_local(str(index_folder_path))
            return vectorstore
        else: 
            print("index already exists, loading...")
            return FAISS.load_local(str(index_folder_path), embeddings, allow_dangerous_deserialization=True)

    def search(vectorstore: FAISS, query: str) -> list[tuple[Document, float]]:
        docs_with_scores = vectorstore.similarity_search_with_score(query, k=4)
    
        # LangChain은 Document와 점수를 반환합니다.
        return [(doc, score) for doc, score in docs_with_scores]

    def main():
        index_folder_path = Path("faiss_index")
    
        vectorstore = create_if_not_exist(index_folder_path)

        doc_list = search(vectorstore, "비트멘 가격 트렌드")
        for doc, score in doc_list:
            print(score, repr(doc.page_content)[:40], "...")

    if __name__ == "__main__":
        main()
    ```

    실행하면, `faiss_index` 이름의 폴더에 `index.faiss` 파일과 `index.pkl` 파일이 생성됩니다.

    ??? 실행결과

        ```
        creating new index...
        1.5401853 'Argus Bitumen\n\nIssue 24-12  Friday 22 ...
        1.5486758 'Ⓡ\n\n# argus\n\n# Argus Bitumen\n\nEuro ...
        1.5860863 "Argus Bitumen\n\nIssue 24-12  Friday 22 ...
        1.5874922 'Argus Bitumen\n\nIssue 24-12  Friday 22 ...
        ```
    
        다시 실행하면 기존 인덱스를 로딩하여 유사 문서 검색을 수행합니다.
    
        ```
        index already exists, loading...
        1.5401853 'Argus Bitumen\n\nIssue 24-12  Friday 22 ...
        1.5486758 'Ⓡ\n\n# argus\n\n# Argus Bitumen\n\nEuro ...
        1.5860863 "Argus Bitumen\n\nIssue 24-12  Friday 22 ...
        1.5874922 'Argus Bitumen\n\nIssue 24-12  Friday 22 ...
        ```

## 검색된 유사 문서 기반으로 RAG 수행하기

``` py linenums="1" hl_lines="8"
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI

# ...

def main():
    # ...
    doc_list: list[Document] = ...  # 위에서 검색된 문서 리스트

    # 검색된 문서 내용 출력
    print(f"쿼리: {query}\n")
    print("검색된 관련 문서:")
    for i, (doc, score) in enumerate(doc_list, 1):
        print(f"\n문서 {i} (유사도 점수: {score:.4f})")
        print(f"내용: {repr(doc.page_content[:200])} ...")
        print(f"출처: {doc.metadata.get('source', '정보 없음')}")
    
    # RAG 수행: 검색된 문서를 기반으로 응답 생성
    llm = ChatOpenAI(model="gpt-4o-mini")
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm, chain_type="stuff", retriever=vectorstore.as_retriever(), return_source_documents=True
    )
    
    # RAG 응답 생성 및 출력
    result = qa_chain.invoke({"query": query})
    print("\n=== RAG 응답 ===")
    print(result["result"])
    print("\n=== 참조 문서 ===")
    for i, doc in enumerate(result["source_documents"], 1):
        print(f"\n참조 {i}: {doc.metadata.get('source', '정보 없음')}")
```

??? 실행결과

    ```
    index already exists, loading...
    쿼리: 비트멘 가격 트렌드
    
    검색된 관련 문서:
    
    문서 1 (유사도 점수: 1.5359)
    내용: 'Argus Bitumen\n\nIssue 24-12  Friday 22 March 2024\n\n# WATERBORNE BITUMEN PRICES, FOB\n\n![image](p002/24-figure.jpg)\nRotterdam\n$485/t Italy Baltic\n$456/t $472/t\nGreece\nSpain\n$456/t South Korea\n$459/t\n$404' ...
    출처: argus-bitumen.pdf
    
    문서 2 (유사도 점수: 1.5468)
    내용: 'Ⓡ\n\n# argus\n\n# Argus Bitumen\n\nEurope, Africa, Middle East and Asia-Pacific prices and commentary\nIncorporating Argus Asphalt Report\n\nargusmedia.com\n\nIssue 24-12 I Friday 22 March 2024\n\nSUMMARY\n\nBitumen' ...
    출처: argus-bitumen.pdf
    
    문서 3 (유사도 점수: 1.5844)
    내용: 'Argus Bitumen\n\nIssue 24-12  Friday 22 March 2024\n\nNORTH AND CENTRAL EUROPE MARKET COMMENTARY\n\n# Summary\n\nDisruption at two French refineries continued to squeeze\noverall bitumen supply in northwest Eu' ...
    출처: argus-bitumen.pdf
    
    === RAG 응답 ===
    비트멘 가격은 최근 몇 주 동안 유럽의 많은 지역에서 상승세를 보이고 있습니다. 이는 주로 북서 유럽의 공급이 조여지고, 연료유 가격이 강세를 보이기 때문입니다. 특히 로테르담과 발틱 지역의 비트멘 가격 차별이 증가했습니다. 반면 아시아에서는 수요가 약세를 보이며 싱가포르와 한국의 비트멘 가격이 하락했습니다.
    
    유럽에서 봄 날씨가 따뜻해지면서 지중해 비트멘 시장의 활동과 수요가 증가하고 있으며, 이는 일부 시장에서 국내 화물 가격 상승으로 이어졌습니다. 전체적으로 보았을 때, 유럽 시장에서는 가격 상승세가 이어지는 반면, 아시아 시장에서는 수요 부족으로 가격이 하락하고 있는 양상을 보이고 있습니다.
    
    === 참조 문서 ===
    
    참조 1: argus-bitumen.pdf
    
    참조 2: argus-bitumen.pdf
    
    참조 3: argus-bitumen.pdf
    ```