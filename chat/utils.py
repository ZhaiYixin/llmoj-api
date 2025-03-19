import tiktoken

def _count_tokens(text):
    # 粗略估算token数量
    if not hasattr(_count_tokens, "encoding"):
        _count_tokens.encoding = tiktoken.encoding_for_model("gpt-4")
    tokens = _count_tokens.encoding.encode(text)
    return len(tokens)
