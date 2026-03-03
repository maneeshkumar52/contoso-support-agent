"""Recursive text chunker for document indexing."""
import re
from dataclasses import dataclass, field
from typing import List, Optional
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class DocumentChunk:
    """A chunk of a document with metadata."""
    content: str
    source_file: str
    title: str
    chunk_index: int
    section_heading: Optional[str] = None
    page_number: Optional[int] = None
    category: str = "general"
    clearance_level: str = "general"


class RecursiveTextChunker:
    """
    Splits text recursively on paragraph, sentence, and word boundaries.
    Preserves section heading metadata.
    """

    SEPARATORS = ["\n\n", "\n", ". ", " "]

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200) -> None:
        """
        Initialize the chunker.

        Args:
            chunk_size: Target size of each chunk in characters.
            chunk_overlap: Number of characters to overlap between chunks.
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def _split_text(self, text: str, separators: List[str]) -> List[str]:
        """Recursively split text using the separator hierarchy."""
        if not separators:
            return [text]

        separator = separators[0]
        remaining = separators[1:]

        splits = text.split(separator)
        chunks = []
        current = ""

        for split in splits:
            if len(current) + len(split) + len(separator) <= self.chunk_size:
                current += (separator if current else "") + split
            else:
                if current:
                    chunks.append(current)
                if len(split) > self.chunk_size and remaining:
                    chunks.extend(self._split_text(split, remaining))
                else:
                    current = split

        if current:
            chunks.append(current)

        return chunks

    def _add_overlap(self, chunks: List[str]) -> List[str]:
        """Add overlap between consecutive chunks."""
        if len(chunks) <= 1:
            return chunks

        overlapped = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_end = chunks[i - 1][-self.chunk_overlap:] if len(chunks[i - 1]) > self.chunk_overlap else chunks[i - 1]
            overlapped.append(prev_end + "\n" + chunks[i])

        return overlapped

    def _extract_heading(self, text: str) -> Optional[str]:
        """Extract section heading from text if present."""
        lines = text.strip().split("\n")
        for line in lines[:3]:
            if line.startswith("#") or (line and line[0].isupper() and len(line) < 80):
                return line.strip("# ").strip()
        return None

    def chunk_document(
        self,
        text: str,
        source_file: str,
        title: str,
        category: str = "general",
        clearance_level: str = "general",
    ) -> List[DocumentChunk]:
        """
        Chunk a document into overlapping pieces with metadata.

        Args:
            text: The full document text.
            source_file: The source filename.
            title: Document title.
            category: Document category.
            clearance_level: Access clearance level.

        Returns:
            List of DocumentChunk objects.
        """
        raw_chunks = self._split_text(text, self.SEPARATORS)
        overlapped_chunks = self._add_overlap(raw_chunks)

        document_chunks = []
        for i, chunk_text in enumerate(overlapped_chunks):
            if len(chunk_text.strip()) < 50:  # Skip tiny chunks
                continue
            chunk = DocumentChunk(
                content=chunk_text.strip(),
                source_file=source_file,
                title=title,
                chunk_index=i,
                section_heading=self._extract_heading(chunk_text),
                category=category,
                clearance_level=clearance_level,
            )
            document_chunks.append(chunk)

        logger.info(
            "document_chunked",
            source_file=source_file,
            num_chunks=len(document_chunks),
            chunk_size=self.chunk_size,
        )
        return document_chunks

    def split_text(self, text: str, metadata: dict = None) -> list:
        """
        Split text into chunks as plain dicts (convenience wrapper for demo/testing).

        Args:
            text: The full document text.
            metadata: Optional metadata dict merged into each chunk.

        Returns:
            List of dicts with 'content' and metadata keys.
        """
        if metadata is None:
            metadata = {}
        source_file = metadata.get("source", "unknown")
        title = metadata.get("title", source_file)
        raw_chunks = self._split_text(text, self.SEPARATORS)
        overlapped_chunks = self._add_overlap(raw_chunks)
        result = []
        for i, chunk_text in enumerate(overlapped_chunks):
            if len(chunk_text.strip()) < 50:
                continue
            chunk_dict = {"content": chunk_text.strip(), "chunk_index": i}
            chunk_dict.update(metadata)
            result.append(chunk_dict)
        return result
