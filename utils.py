from typing import List
import re


def normalize_name(name: str) -> str:
    normalizedName = name.replace("أ", "ا").replace("آ", "ا").replace("إ", "ا")
    normalizedName = normalizedName.replace("ة", "ه")
    normalizedName = normalizedName.replace("ئ", "ي")
    normalizedName = normalizedName.replace("ؤ", "و")
    normalizedName = normalizedName.replace("ظ", "ض")
    normalizedName = normalizedName.replace("زينلعابدين", "زينالعابدين")
    normalizedName = normalizedName.replace("زينعابدين", "زينالعابدين")
    normalizedName = normalizedName.replace("عبدالرحمان", "عبدالرحمن")
    return normalizedName


# Helper function to split a list into chunks of `size`
def chunks(lst: List, size: int) -> List[List]:
    return [lst[i : i + size] for i in range(0, len(lst), size)]


def parse_person_callback_data(data: str):
    pattern = r"{(\w+):(\d+),(\w+):(\d+)}"
    match = re.match(pattern, data)

    result = {
        match.group(1): int(match.group(2)),
        match.group(3): int(match.group(4)),
    }
    return result
