"""Vietnamese question bank. Append items to preserve existing IDs."""
import json
from pathlib import Path
BINS = {
    'recycle': ('♻️ Tái chế', 'Làm rỗng, giữ sạch và khô; giao cho đơn vị thu gom tái chế.'),
    'organic': ('🌱 Hữu cơ', 'Tách khỏi bao bì; có thể ủ phân khi có hệ thống phù hợp.'),
    'hazard': ('🔋 Nguy hại', 'Để riêng, không đốt hoặc đổ xuống cống; giao cho điểm thu gom chuyên dụng.'),
    'ewaste': ('🔌 Điện tử', 'Giao cho điểm thu hồi điện tử; không tự tháo hoặc đốt.'),
    'other': ('🗑️ Còn lại', 'Thu gom riêng theo hướng dẫn địa phương.')
}
MODES = {
    'quiz': {'name': 'Quiz xanh', 'length': 100, 'seconds': 0},
    'quick': {'name': 'Phân loại nhanh', 'length': 20, 'seconds': 8},
    'tf': {'name': 'Đúng / Sai', 'length': 30, 'seconds': 0},
    'timed': {'name': 'Chạy đua thời gian', 'length': 20, 'seconds': 15}
}
TRASH_DATA = json.loads(Path(__file__).with_name('trash_data.json').read_text(encoding='utf-8'))
ITEMS = [(name, category) for category, names in TRASH_DATA.items() for name in names]

def generate_questions():
    bank = []
    for i, (name, category) in enumerate(ITEMS):
        texts = [f'{name} nên được phân vào nhóm nào?',
                 f'Khi dọn nhà, bạn thấy {name.lower()}. Hãy chọn nhóm rác phù hợp.',
                 f'Để tránh trộn lẫn rác, hãy phân loại {name.lower()}.']
        for v, text in enumerate(texts):
            bank.append({'id': i * 3 + v, 'text': text, 'item': name,
                         'answer': category, 'tip': BINS[category][1]})
    return bank

QUESTIONS = generate_questions()

def question(qid, mode, round_number):
    q = dict(QUESTIONS[qid])
    q['options'] = [{'id': k, 'label': v[0]} for k, v in BINS.items()]
    if mode == 'quick':
        q['text'] = q['item']
    if mode == 'tf':
        keys = list(BINS)
        actual = keys.index(q['answer'])
        claimed = keys[actual if (qid + round_number) % 2 == 0 else (actual + 1 + qid % 4) % len(keys)]
        q['text'] = f"{q['item']} thuộc nhóm {BINS[claimed][0]}."
        q['answer'] = 'true' if claimed == q['answer'] else 'false'
        q['options'] = [{'id': 'true', 'label': 'Đúng'}, {'id': 'false', 'label': 'Sai'}]
    return q

if __name__ == '__main__':
    print(f'{len(ITEMS)} vật phẩm; {len(QUESTIONS)} câu hỏi')
