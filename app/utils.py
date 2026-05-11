import re

def generate_record_id(records):
    """
    Generates a sequential record ID (e.g., RXMED001).
    Safely finds the highest existing number to avoid duplicates,
    even if earlier records were deleted. Handles both dicts and ORM objects.
    """
    if not records:
        return "RXMED001"

    max_num = 0
    for record in records:
        # Handle both dictionaries (JSON) and SQLAlchemy ORM objects safely
        last_id = record.get("record_id", "") if isinstance(record, dict) else getattr(record, "record_id", "")
        
        # Search for digits at the end of the ID string
        match = re.search(r'(\d+)$', last_id)
        if match:
            num = int(match.group(1))
            if num > max_num:
                max_num = num

    # If no valid numbers found (e.g. handling old RX83EB... formats), start at 1
    number = max_num + 1 if max_num > 0 else 1
    
    return f"RXMED{number:03d}"