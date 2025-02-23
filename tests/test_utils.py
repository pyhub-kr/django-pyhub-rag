import pytest
import tiktoken

from pyhub.rag.utils import aenumerate, make_groups_by_length


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
