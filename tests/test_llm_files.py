from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile, File
from PIL import Image as PILImage

from pyhub.llm.utils.files import FileType, encode_files


def create_test_png_image(width=100, height=100, color="white") -> File:
    """테스트용 이미지 파일 생성"""
    image = PILImage.new("RGB", (width, height), color)
    image_io = BytesIO()
    image.save(image_io, format="PNG")
    image_io.seek(0)
    return ContentFile(image_io.read(), name="test_image.png")


def create_test_text_file() -> File:
    """테스트용 텍스트 파일 생성"""
    content = "This is a test text file."
    return ContentFile(content.encode("utf-8"), name="test_file.txt")


class TestEncodeFiles:
    def test_encode_image_files_to_base64(self):
        """이미지 파일을 base64로 인코딩하는 기능 테스트"""
        # 테스트 이미지 생성
        png_file = create_test_png_image()

        # 인코딩 실행
        encoded_urls = encode_files(files=[png_file], allowed_types=FileType.IMAGE, convert_mode="base64")

        # 검증
        assert len(encoded_urls) == 1
        assert encoded_urls[0].startswith("data:image/png;base64,")

    def test_encode_multiple_image_files(self):
        """여러 이미지 파일을 인코딩하는 기능 테스트"""
        png_files = [create_test_png_image(100, 100, "red"), create_test_png_image(200, 200, "blue")]

        encoded_urls = encode_files(files=png_files, allowed_types=FileType.IMAGE, convert_mode="base64")

        assert len(encoded_urls) == 2
        assert all(url.startswith("data:image/png;base64,") for url in encoded_urls)

    def test_filter_by_allowed_types(self):
        """허용된 파일 타입만 인코딩하는 기능 테스트"""
        files = [create_test_png_image(), create_test_text_file()]  # 이미지 파일  # 텍스트 파일

        # 이미지만 허용
        encoded_urls = encode_files(files=files, allowed_types=FileType.IMAGE, convert_mode="base64")

        assert len(encoded_urls) == 1
        assert encoded_urls[0].startswith("data:image/png;base64,")

        # 텍스트만 허용
        encoded_urls = encode_files(files=files, allowed_types=FileType.TEXT, convert_mode="base64")

        assert len(encoded_urls) == 1
        assert encoded_urls[0].startswith("data:text/plain;base64,")

    def test_empty_files_list(self):
        """빈 파일 리스트 처리 테스트"""
        encoded_urls = encode_files(files=None)
        assert encoded_urls == []

        encoded_urls = encode_files(files=[])
        assert encoded_urls == []

    def test_multiple_allowed_types(self):
        """여러 허용 타입 지정 테스트"""
        files = [create_test_png_image(), create_test_text_file()]

        encoded_urls = encode_files(files=files, allowed_types=[FileType.IMAGE, FileType.TEXT], convert_mode="base64")

        assert len(encoded_urls) == 2

    def test_path_string_input(self, tmp_path):
        """경로 문자열 입력 테스트"""
        # 임시 이미지 파일 생성
        img_path = tmp_path / "test_img.png"
        img = PILImage.new("RGB", (100, 100), "white")
        img.save(img_path)

        encoded_urls = encode_files(files=[str(img_path)], allowed_types=FileType.IMAGE, convert_mode="base64")

        assert len(encoded_urls) == 1
        assert encoded_urls[0].startswith("data:image/png;base64,")

    def test_path_object_input(self, tmp_path):
        """Path 객체 입력 테스트"""
        # 임시 이미지 파일 생성
        img_path = tmp_path / "test_img.png"
        img = PILImage.new("RGB", (100, 100), "white")
        img.save(img_path)

        encoded_urls = encode_files(files=[Path(img_path)], allowed_types=FileType.IMAGE, convert_mode="base64")

        assert len(encoded_urls) == 1
        assert encoded_urls[0].startswith("data:image/png;base64,")

    def test_image_resizing(self):
        """이미지 리사이징 테스트"""
        # 큰 이미지 생성
        large_image = create_test_png_image(1000, 800)

        # 기본 max_size로 인코딩
        encoded_urls = encode_files(
            files=[large_image],
            allowed_types=FileType.IMAGE,
            convert_mode="base64",
            image_max_size=300,  # 더 작은 크기로 리사이징
        )

        assert len(encoded_urls) == 1
        assert encoded_urls[0].startswith("data:image/png;base64,")

        # 리사이징된 이미지는 원본보다 base64 문자열이 짧아야 함
        large_image.seek(0)
        encoded_large = encode_files(
            files=[large_image],
            allowed_types=FileType.IMAGE,
            convert_mode="base64",
            image_max_size=1000,  # 원본 크기 유지
        )

        assert len(encoded_large[0]) > len(encoded_urls[0])

    def test_optimize_jpeg(self):
        """optimize_jpeg 옵션 테스트"""
        # 복잡한 이미지 생성 (그라데이션 패턴)
        complex_image = PILImage.new("RGB", (500, 500), "white")
        pixels = complex_image.load()
        for i in range(complex_image.width):
            for j in range(complex_image.height):
                pixels[i, j] = (i % 256, j % 256, (i + j) % 256)  # 그라데이션 패턴

        image_io = BytesIO()
        complex_image.save(image_io, format="PNG")
        image_io.seek(0)
        complex_file = ContentFile(image_io.read(), name="complex.png")

        # optimize_jpeg=False로 인코딩
        complex_file.seek(0)
        encoded_orig = encode_files(
            files=[complex_file],
            allowed_types=FileType.IMAGE,
            convert_mode="base64",
            optimize_jpeg=False,
            image_quality=90,  # 높은 품질
        )

        # optimize_jpeg=True로 인코딩
        complex_file.seek(0)
        encoded_optimized = encode_files(
            files=[complex_file],
            allowed_types=FileType.IMAGE,
            convert_mode="base64",
            optimize_jpeg=True,
            image_quality=20,  # 낮은 품질
        )

        # 두 이미지 모두 올바른 형식인지 확인
        assert encoded_orig[0].startswith("data:image/png;base64,")
        assert encoded_optimized[0].startswith("data:image/jpeg;base64,")
