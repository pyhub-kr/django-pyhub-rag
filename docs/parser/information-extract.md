# Information Extract API 사용법

Upstage Information Extract API를 사용하여 문서에서 구조화된 정보를 자동으로 추출할 수 있습니다.

## 주요 기능

- **Universal Information Extraction**: 범용 추출 - 사용자 정의 스키마에 맞춰 추출
- **Prebuilt Information Extraction**: 사전 학습 모델 - 특정 문서 타입에 최적화
- **배치 처리**: 여러 문서를 한 번에 처리
- **Django 통합**: 추출 결과를 데이터베이스에 저장

## CLI 사용법

### 기본 사용법

```bash
# 간단한 키 추출
pyhub.parser upstage_extract invoice.pdf --keys "invoice_date,total_amount,vendor_name"

# 스키마를 사용한 추출
pyhub.parser upstage_extract invoice.pdf --schema examples/extraction_schemas/invoice_schema.json

# Prebuilt 모델 사용
pyhub.parser upstage_extract invoice.pdf --type prebuilt --document-type invoice
```

### 배치 처리

```bash
# 디렉토리 내 모든 문서 처리
pyhub.parser upstage_extract --batch-dir ./documents/ --schema invoice_schema.json

# 결과는 documents/extracted/ 폴더에 저장됩니다
```

### 옵션 설명

- `--schema, -s`: JSON 스키마 파일 경로
- `--keys, -k`: 추출할 키 목록 (쉼표로 구분)
- `--type, -t`: 추출 타입 (universal/prebuilt)
- `--document-type, -d`: 문서 타입 (prebuilt 모드에서 필수)
- `--format, -f`: 출력 포맷 (json/jsonl/csv)
- `--batch-dir, -b`: 배치 처리할 디렉토리

## 스키마 정의

### 송장 스키마 예제

```json
{
  "document_information": {
    "document_number": {"type": "string"},
    "issue_date": {"type": "string", "format": "date"}
  },
  "vendor_information": {
    "vendor_name": {"type": "string"},
    "vendor_address": {"type": "string"}
  },
  "financial_summary": {
    "total_amount": {"type": "number"},
    "currency": {"type": "string"}
  }
}
```

### 계약서 스키마 예제

```json
{
  "contract_information": {
    "contract_title": {"type": "string"},
    "effective_date": {"type": "string", "format": "date"},
    "expiration_date": {"type": "string", "format": "date"}
  },
  "parties": {
    "type": "array",
    "items": {
      "party_name": {"type": "string"},
      "party_type": {"type": "string"}
    }
  }
}
```

## Django 통합

### Management Command

```bash
# 특정 문서에서 추출
python manage.py extract_information --document-id 123 --schema-file invoice_schema.json

# 모든 미처리 문서 처리
python manage.py extract_information --all-pending --keys "invoice_date,total_amount"
```

### Python API

```python
from pyhub.parser.upstage import UpstageInformationExtractor, ExtractionSchema

# 추출기 생성
extractor = UpstageInformationExtractor(
    api_key="your_api_key",
    extraction_type="universal"
)

# 스키마 로드
schema = ExtractionSchema.from_json_file("invoice_schema.json")

# 추출 실행
with open("invoice.pdf", "rb") as f:
    result = extractor.extract_sync(
        file=f,
        schema=schema
    )
    print(result)
```

### 모델 사용

```python
from pyhub.doku.models import Document, ExtractedInformation

# 문서에서 정보 추출
document = Document.objects.get(pk=1)
extracted = ExtractedInformation.objects.create(
    document=document,
    schema_name="invoice",
    extraction_type="universal",
    extracted_data=result
)

# 추출된 정보 조회
for info in document.extracted_information_set.all():
    print(info.extracted_data)
```

## 지원 문서 타입

### Universal Extraction
- PDF
- 이미지 (PNG, JPG, JPEG, BMP, TIFF)
- 스캔된 문서
- 복잡한 레이아웃 문서

### Prebuilt Models
- `invoice`: 송장, 청구서
- `receipt`: 영수증
- `contract`: 계약서
- `form`: 신청서, 양식
- `report`: 보고서

## 활용 사례

1. **자동 송장 처리**
   - 공급업체명, 날짜, 금액 자동 추출
   - ERP 시스템 연동

2. **계약서 관리**
   - 계약 기간, 당사자 정보 추출
   - 만료일 알림 시스템

3. **문서 분류 및 검색**
   - 추출된 메타데이터로 자동 분류
   - 구조화된 검색 가능

## 비용 최적화

- 문서당 과금 방식
- 캐싱을 통한 중복 호출 방지
- 배치 처리로 효율성 향상

## 문제 해결

### API 키 오류
```bash
export UPSTAGE_API_KEY="up_your_api_key"
```

### 추출 실패
- 문서 품질 확인 (해상도, 스캔 상태)
- 스키마 검증
- API 응답 확인

### 성능 최적화
- 배치 크기 조정
- 비동기 처리 활용
- 캐시 활용