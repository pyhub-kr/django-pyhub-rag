import re
from typing import cast

from django.core.exceptions import ValidationError

from pyhub.parser.upstage import UpstageDocumentParseParser
from pyhub.parser.upstage.types import DocumentSplitStrategyType


def run_document_parse_job(document_parse_job_pk: int) -> None:
    from .models import Document, DocumentParseJob, VectorDocument, VectorDocumentImage

    try:
        job = DocumentParseJob.objects.get(pk=document_parse_job_pk)

        job.processing()

        image_descriptor = job.document.get_image_descriptor()
        parser = UpstageDocumentParseParser(
            split=cast(DocumentSplitStrategyType, job.document.split_strategy),
            image_descriptor=image_descriptor,
            base64_encoding_category_list=["figure", "chart", "table"],
            ignore_element_category_list=["footer"],
            pages=job.document.pages or None,
            start_page=job.document.start_page,
            max_page=job.document.max_page,
        )

        parser.is_valid(job.document.file, raise_exception=True)
    except Document.DoesNotExist as e:
        raise e
    except ValidationError as e:
        raise e

    try:
        for pyhub_doc in parser.lazy_parse(
            job.document.file,
            batch_page_size=10,
            ignore_validation=True,
        ):
            pyhub_doc.metadata.setdefault("source", job.document.name)

            # job.document

            document = VectorDocument.objects.create(
                document=job.document,
                page_content=pyhub_doc.page_content,
                metadata=pyhub_doc.metadata,
            )

            # 매 document를 순회하며 지정 variants 값을 읽어와서 파일에 추가
            # variant_page_content = document.variants.get("markdown")

            vector_document_image_list = []
            for el in pyhub_doc.elements:
                if el.files:
                    html: str = el.image_descriptions

                    # 프롬프트가 아닌 Parser 내에 정의된 패턴 : <image name="...">...</image>
                    matches = re.findall(r"(<image\s+name=[\'\"](.*?)[\'\"]>.*?</image>)", html, re.DOTALL)
                    image_dict = {name: full_tag.strip() for full_tag, name in matches}

                    for name, _file in el.files.items():
                        description = image_dict.get(name) or ""

                        vector_document_image_list.append(
                            VectorDocumentImage(
                                vector_document=document,
                                file=_file,
                                name=name,
                                description=description,
                            )
                        )

            VectorDocumentImage.objects.bulk_create(vector_document_image_list, batch_size=50)
    except Exception as e:
        job.failed(e)
    else:
        job.completed()
