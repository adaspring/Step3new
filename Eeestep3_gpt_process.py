# step3_gpt_process.py
import json
import openai
import time
import argparse
from pathlib import Path

def build_gpt_friendly_input(context_file, translated_file, output_file, target_lang):
    """Generate GPT-ready input with language context"""
    with open(context_file, 'r', encoding='utf-8') as f:
        context_data = json.load(f)
    
    with open(translated_file, 'r', encoding='utf-8') as f:
        translated_map = json.load(f)
    
    lines = []
    for category in ['1_word', '2_words', '3_words', '4_or_more_words']:
        for entry in context_data[category]:
            for key, source_text in entry.items():
                if key == 'tag': continue
                translated_text = translated_map.get(key, "")
                tag = entry['tag']
                
                lines.append(f"{key} | {tag}")
                lines.append(f"{args.primary_lang}: {source_text}")
                lines.append(f"{target_lang}: {translated_text}")
                lines.append("")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

def process_with_api(input_file, output_file, api_key, args, max_retries=3):
    """Process translations with dynamic language validation"""
    client = openai.OpenAI(api_key=api_key)
    
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read().split("\n\n")
    
    system_prompt = f"""Improve the {args.target_lang} translation while preserving:
- Technical terms from {args.primary_lang}{f'/{args.secondary_lang}' if args.secondary_lang else ''}
- HTML tag context requirements
- BLOCK_ID references
Return ONLY the improved {args.target_lang} line."""
    
    results = []
    for entry in content:
        if not entry.strip(): continue
        
        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": entry.strip()}
                    ],
                    temperature=0.2,
                    max_tokens=1000
                )
                
                improved_trans = response.choices[0].message.content.strip()
                results.append(f"{entry.strip()}\n{args.target_lang}: {improved_trans}\n")
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    results.append(f"{entry.strip()}\n# ERROR: {str(e)[:50]}\n")
                time.sleep(2 ** attempt)
        
        time.sleep(1)  # Rate limit buffer
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("\n\n".join(results))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GPT Translation Processor")
    parser.add_argument("--context", required=True, help="translatable_flat_sentences.json")
    parser.add_argument("--translated", required=True, help="translations.json")
    parser.add_argument("--output", default="gpt_processed.txt")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--primary-lang", required=True)
    parser.add_argument("--secondary-lang")
    parser.add_argument("--target-lang", required=True)
    
    args = parser.parse_args()
    
    # Generate GPT-ready input
    build_gpt_friendly_input(
        args.context,
        args.translated,
        gpt_input.txt,
        args.primary_lang,
        args.target_lang
    )
    
    # Process with API
    process_with_api(
        gpt_input.txt,
        args.output,
        args.api_key,
        args
    )
