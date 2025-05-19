# step3_gpt_process.py
import json
import openai
import time
import argparse
from pathlib import Path

def validate_input_files(*files):
    """Ensure all input files exist before processing"""
    for file in files:
        if not Path(file).exists():
            raise FileNotFoundError(f"Critical file missing: {file}")

def build_gpt_friendly_input(context_file, translated_file, output_file, target_lang, args):
    """Generate GPT-ready input from Step 1/2 outputs"""
    validate_input_files(context_file, translated_file)
    
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
                tag = entry['tag'].strip('<>')
                
                # Validation
                if not key.startswith("BLOCK_"):
                    raise ValueError(f"Invalid key: {key} in {category}")
                if "<" not in tag or ">" not in tag:
                    raise ValueError(f"Malformed tag: {tag} for {key}")
                
                lines.append(f"{key} | <{tag}>")
                lines.append(f"{args.primary_lang}: {source_text}")
                lines.append(f"{target_lang}: {translated_text}")
                lines.append("")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

def process_with_api(input_file, api_key, args):
    """Process translations via OpenAI API"""
    validate_input_files(input_file)
    client = openai.OpenAI(api_key=api_key)
    
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read().split("\n\n")
    
    system_prompt = f"""Improve {args.target_lang} translation preserving:
- Terms from {args.primary_lang}{f'/{args.secondary_lang}' if args.secondary_lang else ''}
- HTML tag context
- BLOCK_IDs
Return ONLY the {args.target_lang} line."""
    
    results = []
    for entry in content:
        if not entry.strip(): continue
        
        for attempt in range(3):
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
                improved = response.choices[0].message.content.strip()
                results.append(f"{entry.strip()}\n{args.target_lang}: {improved}\n")
                break
            except Exception as e:
                if attempt == 2:
                    results.append(f"{entry.strip()}\n# ERROR: {str(e)[:50]}\n")
                time.sleep(2 ** attempt)
        time.sleep(1)
    
    # Save raw output
    text_output = f"gpt_raw_{args.target_lang}.txt"
    with open(text_output, 'w', encoding='utf-8') as f:
        f.write("\n\n".join(results))
    
    return text_output

def parse_translations(raw_file, target_lang):
    """Convert raw GPT output to JSON"""
    validate_input_files(raw_file)
    translation_map = {}
    
    with open(raw_file, 'r', encoding='utf-8') as f:
        entries = f.read().split("\n\n")
    
    for entry in entries:
        lines = entry.strip().split('\n')
        if len(lines) < 3: continue
        
        block_line, target_line = lines[0], lines[-1]
        if not block_line.startswith("BLOCK_") or f"{target_lang}:" not in target_line:
            continue
        
        block_id = block_line.split(' | ')[0]
        translated_text = target_line.split(": ", 1)[1]
        translation_map[block_id] = translated_text
    
    json_output = f"openai_translations_{target_lang}.json"
    with open(json_output, 'w', encoding='utf-8') as f:
        json.dump(translation_map, f, indent=2, ensure_ascii=False)
    
    return json_output

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GPT Translation Processor")
    parser.add_argument("--context", required=True, 
                       help="translatable_flat_sentences.json from Step 1")
    parser.add_argument("--translated", required=True, 
                       help="translations.json from Step 2")
    parser.add_argument("--api-key", required=True,
                       help="OpenAI API key")
    parser.add_argument("--primary-lang", required=True,
                       help="Original language code (e.g., EN)")
    parser.add_argument("--secondary-lang",
                       help="Optional secondary language code")
    parser.add_argument("--target-lang", required=True,
                       help="Target language code (e.g., FR)")
    
    args = parser.parse_args()
    
    # Validate inputs
    validate_input_files(args.context, args.translated)
    
    # Generate GPT input
    gpt_input = "gpt_input.txt"
    build_gpt_friendly_input(
        args.context, args.translated, gpt_input,
        args.target_lang, args
    )
    
    # Process with OpenAI API
    raw_output = process_with_api(gpt_input, args.api_key, args)
    
    # Generate final JSON translations
    json_translations = parse_translations(raw_output, args.target_lang)
    print(f"✅ Final translations saved to: {json_translations}")
