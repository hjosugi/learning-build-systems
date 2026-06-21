def greeting(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise ValueError("name is required")
    return f"hello, {cleaned}"

