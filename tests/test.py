
notes = []
def save_note_handler(key: str, content:str, notes:list):
    if not key or not content or not notes:
        return "Key or content are missing"
    my_dict = {
        "key": key,
        "content":content
    }
    notes.append(my_dict)
    
def get_notes_handler(notes:list):
    note_arr = []
    if not notes:
        return "No stored notes found"
    for index, note in enumerate(notes,start=1):
        print(note)
        note_str = f"Note: [{index}] Key:{note["content"]} Content: {note["content"]}"
        note_arr.append(note_str)
    return "\n ".join(note_arr)
