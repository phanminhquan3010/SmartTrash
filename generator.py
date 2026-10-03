import random

TRASH_DATA = {
    "Chai nhựa sạch": "Rác tái chế ♻️",
    "Lon nhôm": "Rác tái chế ♻️",
    "Giấy sạch": "Rác tái chế ♻️",
    "Thùng carton sạch": "Rác tái chế ♻️",
    "Vỏ chuối": "Rác hữu cơ 🌱",
    "Vỏ cam": "Rác hữu cơ 🌱",
    "Lá cây": "Rác hữu cơ 🌱",
    "Bã cà phê": "Rác hữu cơ 🌱",
    "Pin đã sử dụng": "Rác nguy hại 🔋",
    "Thuốc hết hạn": "Rác nguy hại 🔋",
    "Điện thoại hỏng": "Rác điện tử 💻",
    "Bàn phím hỏng": "Rác điện tử 💻"
}

CATEGORIES = ["Rác tái chế ♻️", "Rác hữu cơ 🌱", "Rác nguy hại 🔋", "Rác điện tử 💻"]
TEMPLATES = [
    "{item} thuộc nhóm rác nào?",
    "Nên phân loại {item} vào nhóm nào?",
    "Khi thu gom, {item} thuộc loại rác nào?",
    "Đâu là nhóm rác phù hợp với {item}?"
]

def generate_questions(start_id=1000):
    questions = []
    for item, answer in TRASH_DATA.items():
        for template in TEMPLATES:
            options = CATEGORIES.copy()
            random.shuffle(options)
            questions.append({
                "id": start_id + len(questions),
                "question": template.format(item=item),
                "options": options,
                "answer": answer
            })
    random.shuffle(questions)
    return questions
