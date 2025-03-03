from typing import List, Literal, Optional, Union

import pytest
import tiktoken

from pyhub.rag.utils import aenumerate, get_literal_values, make_groups_by_length


@pytest.mark.it("make_groups_by_length 함수가 올바르게 텍스트를 그룹화하는지 테스트합니다.")
def test_make_groups_by_length():
    encoder = tiktoken.encoding_for_model("text-embedding-3-small")

    def length_func(s: str) -> int:
        return len(encoder.encode(s))

    texts = ["one", "two", "three", "four"]
    groups = list(make_groups_by_length(text_list=texts, group_max_length=4, length_func=length_func))

    assert len(groups) == 2
    assert groups[0] == ["one", "two", "three"]
    assert groups[1] == ["four"]


@pytest.mark.it("aenumerate 함수가 올바르게 비동기 생성기에서 인덱스와 아이템 쌍을 생성하는지 테스트합니다.")
@pytest.mark.asyncio
async def test_aenumerate():
    async def async_gen():
        for idx in range(3):
            yield f"item{idx}"

    items = []
    async for i, item in aenumerate(async_gen()):
        items.append((i, item))

    assert items == [(0, "item0"), (1, "item1"), (2, "item2")]


@pytest.mark.it("get_literal_values 함수가 다양한 타입 힌트에서 리터럴 값을 올바르게 추출하는지 테스트합니다.")
def test_get_literal_values():
    # 단일 Literal 테스트
    assert get_literal_values(Literal["a", "b", "c"]) == {"a", "b", "c"}

    # Union 내부의 Literal 테스트
    assert get_literal_values(Union[Literal["x", "y"], Literal["z"]]) == {"x", "y", "z"}

    # Optional(Union[T, None]) 테스트
    assert get_literal_values(Optional[Literal["p", "q"]]) == {"p", "q", None}

    # 중첩된 복합 타입 테스트
    complex_type = Union[Literal["one"], Optional[Literal["two", "three"]]]
    assert get_literal_values(complex_type) == {"one", "two", "three", None}

    # 비 Literal 타입에 대한 테스트
    assert get_literal_values(str) == set()
    assert get_literal_values(List[int]) == set()

    # None 값 테스트
    assert get_literal_values(None) == set()

    # 실제 값 테스트
    assert get_literal_values("actual_value") == {"actual_value"}
