import os
import tempfile
from pathlib import Path
from unittest import TestCase

from django.test import override_settings

from pyhub import init, load_toml, make_settings
from pyhub.parser.upstage.parser import ImageDescriptor


class TestToml(TestCase):
    def setUp(self):
        # 임시 디렉토리 생성
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.toml_path = self.temp_path / "test.toml"

        # 테스트용 설정 초기화
        init(debug=True)

    def tearDown(self):
        # 임시 디렉토리 정리
        self.temp_dir.cleanup()

    def test_load_toml_env_variables(self):
        # 테스트용 TOML 파일 생성
        toml_content = """
        [env]
        TEST_ENV_VAR = "test_value"
        UPSTAGE_API_KEY = "up_test_key"
        """

        with open(self.toml_path, "w", encoding="utf-8") as f:
            f.write(toml_content)

        # TOML 파일 로드
        toml_settings = load_toml(toml_path=self.toml_path, load_env=True)

        # 환경변수 확인
        self.assertIsNotNone(toml_settings)
        self.assertEqual(len(toml_settings.env), 2)
        self.assertEqual(toml_settings.env["TEST_ENV_VAR"], "test_value")
        self.assertEqual(toml_settings.env["UPSTAGE_API_KEY"], "up_test_key")

        # 환경변수가 실제로 설정되었는지 확인
        self.assertEqual(os.environ.get("TEST_ENV_VAR"), "test_value")
        self.assertEqual(os.environ.get("UPSTAGE_API_KEY"), "up_test_key")

    def test_load_toml_prompt_templates(self):
        # 테스트용 프롬프트 템플릿이 포함된 TOML 파일 생성
        toml_content = """
        [prompt_templates.describe_image]
        system = "You are an image descriptor AI."
        user = "Describe this image in detail."
        
        [prompt_templates.describe_table]
        system = "You are a table analyzer AI."
        user = "Analyze this table and provide insights."
        """

        with open(self.toml_path, "w", encoding="utf-8") as f:
            f.write(toml_content)

        # make_settings를 사용하여 Django 설정 구성
        django_settings = make_settings(
            base_dir=self.temp_path,
            toml_path=self.toml_path,
        )

        # 설정에 프롬프트 템플릿이 포함되어 있는지 확인
        prompt_templates = django_settings.PROMPT_TEMPLATES

        # 프롬프트 템플릿 확인
        self.assertIn("describe_image", prompt_templates)
        self.assertIn("describe_table", prompt_templates)
        self.assertEqual(prompt_templates["describe_image"]["system"], "You are an image descriptor AI.")
        self.assertEqual(prompt_templates["describe_image"]["user"], "Describe this image in detail.")
        self.assertEqual(prompt_templates["describe_table"]["system"], "You are a table analyzer AI.")
        self.assertEqual(prompt_templates["describe_table"]["user"], "Analyze this table and provide insights.")

    @override_settings(
        PROMPT_TEMPLATES={
            "describe_image": {
                "system": "You are an image descriptor AI.",
                "user": "Describe this image in detail.",
            },
            "describe_table": {
                "system": "You are a table analyzer AI.",
                "user": "Analyze this table and provide insights.",
            },
        }
    )
    def test_image_descriptor_loads_prompt_templates(self):
        image_descriptor = ImageDescriptor()
        self.assertEqual(image_descriptor.system_prompts["image"], "You are an image descriptor AI.")
        self.assertEqual(image_descriptor.user_prompts["image"], "Describe this image in detail.")
        self.assertEqual(image_descriptor.system_prompts["table"], "You are a table analyzer AI.")
        self.assertEqual(image_descriptor.user_prompts["table"], "Analyze this table and provide insights.")
