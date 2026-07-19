import uuid


def generate_membership_id(user_id: int) -> str:
    return f"MEM-{user_id:05d}-{uuid.uuid4().hex[:6].upper()}"
