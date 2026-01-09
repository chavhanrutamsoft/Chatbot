#!/usr/bin/env python3
"""
IMPROVED QA Pair Extraction - Better Question Generation
Fixes issues with generic "How do I work with..." questions
"""

import json
import re
from docx import Document
from pathlib import Path
from typing import List, Dict, Tuple

# Get project paths
BACKEND_DIR = Path(__file__).parent
PROJECT_ROOT = BACKEND_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"

INPUT_DOCX = DATA_DIR / "08-01-2026.docx"
OUTPUT_QA_JSON = DATA_DIR / "qa_pairs.json"
OUTPUT_CHUNKS_JSON = DATA_DIR / "chunks.json"

def clean_text(text: str) -> str:
    """Clean text and fix encoding issues"""
    if not text:
        return ""
    
    text = text.replace('\ufffd', '')
    text = text.replace('–', '-')
    text = text.replace('—', '-')
    text = text.replace('"', '"')
    text = text.replace('"', '"')
    text = text.replace(''', "'")
    text = text.replace(''', "'")
    text = text.replace('→', '->')
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def is_heading(text: str) -> bool:
    """Check if text looks like a heading"""
    if not text:
        return False
    
    if len(text) < 100 and text.endswith(':'):
        return True
    
    if text.isupper() and len(text) > 3:
        return True
    
    heading_patterns = [
        r'^\d+\.',  # Numbered headings like "1. Overview"
        r'^[A-Z][a-z]+ [A-Z][a-z]+:',  # "Lead Management:"
        r'^Steps? to',  # "Steps to Create"
        r'^How to',  # "How to..."
        r'^Creating',  # "Creating a Lead:"
        r'^Introduction',  # "Introduction"
        r'^Overview',  # "Overview"
    ]
    
    for pattern in heading_patterns:
        if re.match(pattern, text, re.IGNORECASE):
            return True
    
    return False

def extract_steps(text: str) -> List[str]:
    """Extract numbered steps from text"""
    steps = []
    step_pattern = r'(?:^|\n)\s*(\d+[\.\)])\s+(.+?)(?=\n\s*\d+[\.\)]|\n\n|$)'
    matches = re.finditer(step_pattern, text, re.MULTILINE | re.DOTALL)
    
    for match in matches:
        step_text = match.group(2).strip()
        if len(step_text) > 10:
            steps.append(clean_text(step_text))
    
    return steps

def generate_better_question(heading: str, content: str) -> str:
    """Generate a better, more specific question from heading and content"""
    heading = heading.rstrip(':').strip()
    
    # Remove numbering from heading (e.g., "1. Overview" -> "Overview")
    heading = re.sub(r'^\d+\.\s*', '', heading)
    heading = re.sub(r'^\d+\.\d+\.\s*', '', heading)  # Remove "1.1."
    
    # Direct question patterns
    if heading.startswith('How to'):
        return heading.replace('How to', 'How do I') + "?"
    
    if heading.startswith('Steps to'):
        action = heading.replace('Steps to', '').strip()
        # Extract action verb
        if 'create' in action.lower():
            topic = action.replace('Create', '').replace('a', '').strip()
            return f"How do I create a {topic.lower()}?"
        elif 'modify' in action.lower() or 'edit' in action.lower():
            topic = action.replace('Modify', '').replace('Edit', '').replace('a', '').strip()
            return f"How do I modify a {topic.lower()}?"
        elif 'view' in action.lower() or 'see' in action.lower():
            topic = action.replace('View', '').replace('See', '').replace('a', '').strip()
            return f"How do I view a {topic.lower()}?"
        else:
            return f"How do I {action.lower()}?"
    
    if heading.startswith('Creating'):
        topic = heading.replace('Creating', '').replace('a', '').strip()
        return f"How do I create a {topic.lower()}?"
    
    if heading.startswith('What is'):
        return heading + "?"
    
    # Analyze content to determine question type
    content_lower = content.lower()
    
    # Check for procedure/action words in content
    if any(word in content_lower for word in ['navigate', 'click', 'select', 'enter', 'save']):
        # It's a procedure
        if 'create' in content_lower[:200]:
            topic = heading.split(':')[0] if ':' in heading else heading
            return f"How do I create a {topic.lower()}?"
        elif 'modify' in content_lower[:200] or 'edit' in content_lower[:200]:
            topic = heading.split(':')[0] if ':' in heading else heading
            return f"How do I modify a {topic.lower()}?"
        elif 'view' in content_lower[:200]:
            topic = heading.split(':')[0] if ':' in heading else heading
            return f"How do I view a {topic.lower()}?"
        else:
            # Generic procedure
            topic = heading.split(':')[0] if ':' in heading else heading
            # Remove common words
            topic = re.sub(r'\b(overview|introduction|steps?|how|to|with)\b', '', topic, flags=re.IGNORECASE).strip()
            if topic:
                return f"How do I {topic.lower()}?"
    
    # Check for definition/explanation
    if any(word in content_lower[:100] for word in ['is', 'represents', 'means', 'refers to']):
        topic = heading.split(':')[0] if ':' in heading else heading
        topic = re.sub(r'\b(overview|introduction)\b', '', topic, flags=re.IGNORECASE).strip()
        if topic:
            return f"What is {topic.lower()}?"
    
    # Check for overview/introduction
    if 'overview' in heading.lower() or 'introduction' in heading.lower():
        topic = heading.replace('Overview', '').replace('Introduction', '').strip()
        topic = re.sub(r'^\d+\.\s*', '', topic)  # Remove numbering
        if topic:
            return f"What is {topic.lower()}?"
    
    # Default: convert heading to question
    if ':' in heading:
        heading = heading.split(':')[0]
    
    # Remove action words that don't make sense in questions
    heading = re.sub(r'\b(enter|select|click|navigate|work|with)\b', '', heading, flags=re.IGNORECASE).strip()
    
    # If heading is too generic, use content to create question
    if len(heading) < 5 or heading.lower() in ['module', 'section', 'page']:
        # Try to extract topic from content
        first_sentence = content.split('.')[0] if '.' in content else content[:100]
        # Look for key terms
        if 'lead' in first_sentence.lower():
            return "What is a Lead?"
        elif 'timesheet' in first_sentence.lower():
            return "What is a Timesheet?"
        elif 'bom' in first_sentence.lower():
            return "What is a BOM?"
        else:
            return f"What is {heading.lower()}?"
    
    # Final fallback
    if not heading.endswith('?'):
        return f"What is {heading.lower()}?"
    
    return heading

def create_qa_from_procedure(heading: str, content: str) -> List[Dict]:
    """Create QA pairs from a procedure with steps"""
    qa_pairs = []
    
    # Generate better question
    main_question = generate_better_question(heading, content)
    
    # Extract steps
    steps = extract_steps(content)
    
    if steps and len(steps) > 1:
        # Create main answer with steps
        answer = "Follow these steps:\n\n"
        for i, step in enumerate(steps, 1):
            answer += f"{i}. {step}\n"
        
        qa_pairs.append({
            "question": main_question,
            "answer": clean_text(answer),
            "type": "procedure",
            "has_steps": True,
            "step_count": len(steps)
        })
        
        # Don't create individual step QAs (they're too specific)
    else:
        # No steps or single step, just content
        qa_pairs.append({
            "question": main_question,
            "answer": clean_text(content),
            "type": "general",
            "has_steps": False
        })
    
    return qa_pairs

def extract_qa_pairs_from_docx(path: Path) -> Tuple[List[Dict], List[str]]:
    """Extract QA pairs and chunks from document"""
    doc = Document(path)
    qa_pairs = []
    chunks = []
    
    current_heading = None
    current_content = []
    
    for para in doc.paragraphs:
        text = clean_text(para.text)
        if not text:
            # Blank line - finalize current section
            if current_heading and current_content:
                content_text = " ".join(current_content)
                
                # Create QA pairs
                section_qa = create_qa_from_procedure(current_heading, content_text)
                qa_pairs.extend(section_qa)
                
                # Create chunk
                chunk_text = f"{current_heading}\n\n{content_text}"
                if len(chunk_text) > 100:
                    chunks.append(chunk_text)
            
            current_heading = None
            current_content = []
            continue
        
        # Check if this is a heading
        if is_heading(text):
            # Process previous section
            if current_heading and current_content:
                content_text = " ".join(current_content)
                section_qa = create_qa_from_procedure(current_heading, content_text)
                qa_pairs.extend(section_qa)
                
                chunk_text = f"{current_heading}\n\n{content_text}"
                if len(chunk_text) > 100:
                    chunks.append(chunk_text)
            
            # Start new section
            current_heading = text
            current_content = []
        else:
            # Add to current content
            current_content.append(text)
    
    # Process final section
    if current_heading and current_content:
        content_text = " ".join(current_content)
        section_qa = create_qa_from_procedure(current_heading, content_text)
        qa_pairs.extend(section_qa)
        
        chunk_text = f"{current_heading}\n\n{content_text}"
        if len(chunk_text) > 100:
            chunks.append(chunk_text)
    
    # Create chunks from QA pairs for better retrieval
    for qa in qa_pairs:
        qa_chunk = f"Q: {qa['question']}\nA: {qa['answer']}"
        chunks.append(qa_chunk)
    
    return qa_pairs, chunks

def filter_bad_questions(qa_pairs: List[Dict]) -> List[Dict]:
    """Filter out bad quality questions"""
    filtered = []
    
    for qa in qa_pairs:
        question = qa['question'].lower()
        
        # Skip generic "work with" questions
        if question.startswith('how do i work with'):
            # Try to improve it
            topic = qa['question'].replace('How do I work with', '').replace('?', '').strip()
            answer = qa['answer'].lower()
            
            # Determine better question based on answer
            if 'create' in answer[:200] or 'creating' in answer[:200]:
                qa['question'] = f"How do I create a {topic.lower()}?"
            elif 'modify' in answer[:200] or 'edit' in answer[:200]:
                qa['question'] = f"How do I modify a {topic.lower()}?"
            elif 'view' in answer[:200] or 'see' in answer[:200]:
                qa['question'] = f"How do I view a {topic.lower()}?"
            elif len(topic) < 5 or topic in ['enter', 'select', 'click']:
                # Skip this QA - too vague
                continue
            else:
                qa['question'] = f"What is {topic.lower()}?"
        
        # Skip questions that are too short or don't make sense
        if len(qa['question']) < 10:
            continue
        
        # Skip questions like "How do I a lead?" (missing verb)
        if re.match(r'how do i (a|an|the) ', qa['question'].lower()):
            # Fix it
            topic = re.sub(r'how do i (a|an|the) ', '', qa['question'].lower()).replace('?', '').strip()
            qa['question'] = f"How do I create a {topic}?"
        
        # Ensure question ends with ?
        if not qa['question'].endswith('?'):
            qa['question'] += '?'
        
        filtered.append(qa)
    
    return filtered

def main():
    """Main extraction function"""
    print("=" * 80)
    print("IMPROVED QA PAIR EXTRACTION")
    print("=" * 80)
    print()
    
    if not INPUT_DOCX.exists():
        print(f"Error: Document not found at {INPUT_DOCX.resolve()}")
        return
    
    print(f"Reading document: {INPUT_DOCX.name}")
    print("Extracting QA pairs with improved question generation...")
    print()
    
    # Extract QA pairs and chunks
    qa_pairs, chunks = extract_qa_pairs_from_docx(INPUT_DOCX)
    
    print(f"Initial QA pairs: {len(qa_pairs)}")
    
    # Filter and improve questions
    qa_pairs = filter_bad_questions(qa_pairs)
    
    print(f"After filtering: {len(qa_pairs)}")
    
    # Remove duplicates
    seen_questions = set()
    unique_qa_pairs = []
    for qa in qa_pairs:
        q_lower = qa['question'].lower().strip()
        if q_lower not in seen_questions:
            seen_questions.add(q_lower)
            unique_qa_pairs.append(qa)
    
    print(f"After deduplication: {len(unique_qa_pairs)}")
    
    # Statistics
    print("=" * 80)
    print("EXTRACTION STATISTICS")
    print("=" * 80)
    print(f"Total QA Pairs: {len(unique_qa_pairs)}")
    print(f"  - Procedures: {len([q for q in unique_qa_pairs if q.get('type') == 'procedure'])}")
    print(f"  - General: {len([q for q in unique_qa_pairs if q.get('type') == 'general'])}")
    print(f"Total Chunks: {len(chunks)}")
    print(f"Average Chunk Size: {sum(len(c) for c in chunks) / len(chunks):.0f} chars")
    print()
    
    # Check for remaining generic questions
    generic_count = sum(1 for qa in unique_qa_pairs if qa['question'].lower().startswith('how do i work with'))
    if generic_count > 0:
        print(f"⚠️  Warning: {generic_count} generic 'work with' questions still remain")
        print("   Consider manual review of qa_pairs.json")
        print()
    
    # Save QA pairs
    print(f"Saving QA pairs to: {OUTPUT_QA_JSON}")
    with open(OUTPUT_QA_JSON, 'w', encoding='utf-8') as f:
        json.dump(unique_qa_pairs, f, ensure_ascii=False, indent=2)
    
    # Save chunks
    print(f"Saving chunks to: {OUTPUT_CHUNKS_JSON}")
    with open(OUTPUT_CHUNKS_JSON, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    
    print()
    print("=" * 80)
    print("EXTRACTION COMPLETE!")
    print("=" * 80)
    print()
    print("Next steps:")
    print("1. Review QA pairs: python backend/show_qa_samples.py")
    print("2. Check quality: python backend/analyze_qa_quality.py")
    print("3. Ingest into Qdrant: python backend/ingest_qa_qdrant.py")
    print()

if __name__ == "__main__":
    main()
