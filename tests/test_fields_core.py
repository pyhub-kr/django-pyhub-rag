from django.core.exceptions import ValidationError
from django.db import models
from django.forms import ModelForm, TextInput
from django.test import TestCase

from pyhub.core.models.fields import PageNumbersField


class TestModel(models.Model):
    pages = PageNumbersField()
    pages_with_min = PageNumbersField(min_page=5)
    pages_with_range = PageNumbersField(min_page=3, max_page=100)

    class Meta:
        app_label = "test_app"
        managed = False  # 실제 DB 테이블 생성을 방지


class TestForm(ModelForm):
    class Meta:
        model = TestModel
        fields = ["pages", "pages_with_min", "pages_with_range"]


class PageNumbersFieldTest(TestCase):
    def setUp(self):
        self.test_instance = TestModel()
        self.field = PageNumbersField()
        self.field_with_range = PageNumbersField(min_page=3, max_page=100)

    def test_field_initialization(self):
        """필드 초기화 옵션 테스트"""
        # 기본값 테스트
        self.assertEqual(self.field.min_page, 1)
        self.assertIsNone(self.field.max_page)

        # 범위 설정 테스트
        self.assertEqual(self.field_with_range.min_page, 3)
        self.assertEqual(self.field_with_range.max_page, 100)

        # 잘못된 범위 설정 테스트
        with self.assertRaises(ValueError):
            PageNumbersField(min_page=10, max_page=5)

    def test_data_conversion(self):
        """데이터 변환 로직 테스트"""
        test_cases = [
            (None, []),  # None 값 처리
            ("", []),  # 빈 문자열 처리
            ("1,2,3", [1, 2, 3]),  # 기본 문자열 변환
            ("3,1,2,2", [1, 2, 3]),  # 중복 제거 및 정렬
            (" 1, 2 , 3 ", [1, 2, 3]),  # 공백 처리
            ([1, 3, 2], [1, 2, 3]),  # 리스트 입력 처리
        ]

        for input_value, expected in test_cases:
            self.assertEqual(self.field.to_python(input_value), expected, f"Failed for input: {input_value}")

    def test_validation_rules(self):
        """유효성 검사 규칙 테스트"""
        # 기본 필드 검증
        self.field.validate("1,2,3", self.test_instance)

        # 최소값 검증
        field_min_5 = PageNumbersField(min_page=5)
        with self.assertRaises(ValidationError):
            field_min_5.validate("1,5,6", self.test_instance)

        # 범위 검증
        with self.assertRaises(ValidationError):
            self.field_with_range.validate("2,50,101", self.test_instance)

        # 유효한 범위 검증
        self.field_with_range.validate("3,50,100", self.test_instance)

    def test_form_integration(self):
        """폼 통합 테스트"""
        form = TestForm(data={"pages": "1,2,3", "pages_with_min": "5,6,7", "pages_with_range": "3,50,100"})
        is_valid = form.is_valid()
        self.assertTrue(is_valid)

        # 잘못된 데이터로 폼 검증
        form = TestForm(
            data={
                "pages": "0,1,2",  # min_page=1 위반
                "pages_with_min": "4,5,6",  # min_page=5 위반
                "pages_with_range": "3,101",  # max_page=100 위반
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("pages", form.errors)
        self.assertIn("pages_with_min", form.errors)
        self.assertIn("pages_with_range", form.errors)

    def test_database_value_conversion(self):
        """데이터베이스 값 변환 테스트"""
        test_cases = [
            ([], ""),  # 빈 리스트
            ([1, 2, 3], "1,2,3"),  # 기본 변환
            ([3, 1, 2], "1,2,3"),  # 정렬 확인
            ([1, 2, 2, 3], "1,2,3"),  # 중복 제거
        ]

        for input_value, expected in test_cases:
            self.assertEqual(self.field.get_prep_value(input_value), expected, f"Failed for input: {input_value}")

    def test_edge_cases(self):
        """엣지 케이스 처리 테스트"""
        # 특수문자 및 잘못된 형식 처리
        with self.assertRaises(ValidationError):
            self.field.validate("1,a,3", self.test_instance)

        # 음수 처리
        with self.assertRaises(ValidationError):
            self.field.validate("-1,1,2", self.test_instance)

        # 매우 큰 숫자 처리
        field_with_large_max = PageNumbersField(max_page=1000000)
        field_with_large_max.validate("1,999999", self.test_instance)

        # 빈 리스트와 None 값의 일관성
        self.assertEqual(self.field.get_prep_value([]), "")
        self.assertEqual(self.field.get_prep_value(None), "")

    def test_formfield_configuration(self):
        """폼 필드 설정 테스트"""
        form_field = self.field.formfield()

        # 위젯 설정 확인
        self.assertEqual(form_field.widget.attrs["placeholder"], "예: 1,2,4,5")

        # 커스텀 위젯 속성 추가 테스트
        form_field = self.field.formfield(widget=TextInput(attrs={"class": "custom-input"}))
        self.assertEqual(form_field.widget.attrs["class"], "custom-input")

    def test_from_db_value(self):
        """데이터베이스 값 로드 테스트"""
        test_cases = [
            (None, []),  # None 값 처리
            ("", []),  # 빈 문자열 처리
            ("1,2,3", [1, 2, 3]),  # 기본 변환
            (" 1, 2 , 3 ", [1, 2, 3]),  # 공백 처리
            ("3,1,2,2", [1, 2, 3]),  # 중복 및 정렬
        ]

        for db_value, expected in test_cases:
            result = self.field.from_db_value(db_value, None, None)
            self.assertEqual(result, expected, f"Failed for db_value: {db_value}")

    def test_boundary_values(self):
        """경계값 테스트"""
        # 최소값 경계 테스트
        self.field.validate("1", self.test_instance)  # 최소값 정확히
        with self.assertRaises(ValidationError):
            self.field.validate("0", self.test_instance)  # 최소값보다 작음

        # 최대값 경계 테스트 (범위가 있는 필드)
        self.field_with_range.validate("100", self.test_instance)  # 최대값 정확히
        self.field_with_range.validate("3", self.test_instance)  # 최소값 정확히
        with self.assertRaises(ValidationError):
            self.field_with_range.validate("101", self.test_instance)  # 최대값 초과
        with self.assertRaises(ValidationError):
            self.field_with_range.validate("2", self.test_instance)  # 최소값 미만