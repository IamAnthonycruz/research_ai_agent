from langchain_text_splitters import RecursiveCharacterTextSplitter
class Chunk:
    @staticmethod
    def chunk_note(text, source_url, source_title):
        if not text or not source_url or not source_title:
            return []
        splitter = RecursiveCharacterTextSplitter(
            separators=["\n\n",".", " "],
            chunk_size=350,
            chunk_overlap=60,
            length_function=lambda t: len(t.split())
        )
        raw_chunks = splitter.split_text(text)
        return [
            {
                "text": chunk,
                "source": source_url,
                "title": source_title,
                "chunk_index": i
            }
            for i, chunk in enumerate(raw_chunks)
        ]
        
        


