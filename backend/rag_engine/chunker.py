from typing import List

def hybrid_chunker(text: str, max_chars: int = 1000, overlap: int = 100) -> List[str]:
    """
    Splits text semantically by paragraph, and falls back to a word-aware sliding window
    if a paragraph exceeds max_chars (preventing words from being sliced in half).
    """
    chunks = []
    for para in text.split('\n\n'):
        para = para.strip()
        if not para:
            continue
            
        if len(para) <= max_chars:
            chunks.append(para)
        else:
            # Word-aware sliding window splitting
            words = para.split(' ')
            current_chunk = []
            current_len = 0
            
            for word in words:
                word_len = len(word) + 1  # count the space
                if current_len + word_len > max_chars:
                    if current_chunk:
                        chunks.append(" ".join(current_chunk))
                    
                    # Handle edge case of an exceptionally long word
                    if word_len > max_chars:
                        chunks.append(word)
                        current_chunk = []
                        current_len = 0
                    else:
                        # Incorporate overlap words
                        overlap_words = []
                        overlap_len = 0
                        for w in reversed(current_chunk):
                            if overlap_len + len(w) + 1 <= overlap:
                                overlap_words.insert(0, w)
                                overlap_len += len(w) + 1
                            else:
                                break
                        current_chunk = overlap_words + [word]
                        current_len = sum(len(w) + 1 for w in current_chunk)
                else:
                    current_chunk.append(word)
                    current_len += word_len
            
            if current_chunk:
                chunks.append(" ".join(current_chunk))
                
    return chunks
