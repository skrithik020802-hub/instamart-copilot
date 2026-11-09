import os, json, re, time, random
import pandas as pd
import mock_llm

os.makedirs("outputs", exist_ok=True)

tickets = pd.read_csv("data/raw/tickets.csv", keep_default_na=False)

# Redaction patterns
def redact(text):
    text = re.sub(r'[\w\.-]+@[\w\.-]+\.[\w\.]+', '[EMAIL]', text)
    text = re.sub(r'[6-9]\d{9}', '[PHONE]', text)
    text = re.sub(r'ORD-\d{6}', '[ORDER_ID]', text)
    return text

results = []
mock_llm.reset()

seg_df = pd.read_csv("outputs/customer_segments.csv") if os.path.exists("outputs/customer_segments.csv") else pd.DataFrame()
seg_map = dict(zip(seg_df['customer_id'], seg_df['is_premium'])) if not seg_df.empty else {}
name_map = dict(zip(seg_df['customer_id'], seg_df['segment_name'])) if not seg_df.empty else {}

for _, row in tickets.iterrows():
    tid = row['ticket_id']
    cid = row['customer_id']
    txt = row['text']
    
    if not txt.strip():
        results.append({
            'ticket_id': tid, 'customer_id': cid, 'status': 'skipped_empty',
            'category': '', 'segment_name': name_map.get(cid, ''), 'priority': 'NORMAL',
            'route': 'human_review', 'tokens_used': 0
        })
        continue
        
    if mock_llm.est_tokens(txt) > 400:
        results.append({
            'ticket_id': tid, 'customer_id': cid, 'status': 'flagged_long',
            'category': '', 'segment_name': name_map.get(cid, ''), 'priority': 'NORMAL',
            'route': 'human_review', 'tokens_used': 0
        })
        continue
        
    redacted = redact(txt)
    messages = [
        {"role": "system", "content": "CLASSIFY support ticket. Allowed categories: billing, delivery, technical, fraud. Respond JSON: {\"category\": \"...\", \"reason\": \"...\"}"},
        {"role": "user", "content": redacted}
    ]
    
    # Resilient call
    resp = None
    for attempt in range(3):
        try:
            resp = mock_llm.chat(messages)
            break
        except mock_llm.TransientLLMError:
            time.sleep(0.05 * (2**attempt) * random.uniform(0.9, 1.15))
            
    if not resp:
        continue
        
    content = resp.choices[0].message.content
    tokens = resp.usage.total_tokens
    
    cat = "billing"
    status = "classified_json"
    try:
        parsed = json.loads(content)
        cat = parsed.get("category", "billing")
    except:
        words = re.findall(r"[a-z]+", content.lower())
        found = [c for c in ["billing", "delivery", "technical", "fraud"] if c in words]
        if len(found) == 1:
            cat = found[0]
            status = "classified_keyword"
        else:
            status = "flagged_invalid_output"
            
    is_prem = seg_map.get(cid, False)
    if status == 'flagged_invalid_output':
        route, priority = 'human_review', 'NORMAL'
    elif cat == 'fraud':
        route, priority = 'security_team', 'HIGH'
    elif is_prem:
        route, priority = 'premium_desk', 'HIGH'
    else:
        route, priority = 'support_queue', 'NORMAL'
        
    results.append({
        'ticket_id': tid, 'customer_id': cid, 'status': status,
        'category': cat, 'segment_name': name_map.get(cid, ''),
        'priority': priority, 'route': route, 'tokens_used': tokens
    })

pd.DataFrame(results).to_csv("outputs/triage_results.csv", index=False)
pd.DataFrame(results[:50]).to_csv("outputs/triage_budget_demo.csv", index=False)

print("Part C complete.")
