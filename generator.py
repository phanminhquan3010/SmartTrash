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

CATEGORIES = list(dict.fromkeys(TRASH_DATA.values()))
TEMPLATES = [
    "{item} thuộc nhóm rác nào?",
    "Nên phân loại {item} vào nhóm nào?",
    "Khi thu gom, {item} thuộc loại rác nào?",
    "Đâu là nhóm rác phù hợp với {item}?"
]

ACTIONS = [
    ("Pin đã sử dụng", "Đưa đến điểm thu gom pin phù hợp", ["Bỏ vào rác hữu cơ", "Đốt cùng rác", "Vứt xuống sông"]),
    ("Điện thoại hỏng", "Đưa đến điểm thu gom rác điện tử", ["Bỏ vào rác thực phẩm", "Đốt", "Vứt xuống sông"]),
    ("Giấy sạch chỉ dùng một mặt", "Sử dụng tiếp mặt còn lại", ["Vứt ngay", "Ngâm nước", "Đốt"]),
    ("Bình nước cá nhân", "Dùng lại nhiều lần khi còn an toàn", ["Vứt sau một lần", "Đốt sau khi dùng", "Thay mới mỗi ngày"]),
    ("Vỏ rau củ phù hợp", "Ủ phân khi có điều kiện thích hợp", ["Trộn với pin", "Vứt xuống sông", "Đốt trong phòng"]),
    ("Thuốc hết hạn", "Đưa đến nơi tiếp nhận phù hợp theo hướng dẫn địa phương", ["Đổ xuống cống", "Trộn vào thức ăn", "Vứt ra đường"]),
    ("Hộp carton sạch", "Tái sử dụng hoặc thu gom tái chế", ["Đổ xuống cống", "Trộn với pin", "Đốt trong phòng"]),
    ("Vòi nước không sử dụng", "Khóa vòi để tiết kiệm nước", ["Để nước chảy", "Mở hết cỡ", "Để rò rỉ"]),
    ("Đèn trong phòng không có người", "Tắt đèn khi không cần thiết", ["Bật suốt ngày", "Bật thêm đèn", "Không cần quan tâm"]),
    ("Đồ chơi còn tốt không dùng nữa", "Tặng hoặc trao đổi để dùng lại", ["Đốt ngay", "Vứt xuống sông", "Chôn ngoài vườn"]),
]

def generate_questions(start_id=1000):
    """Create a finite bank of fact-based questions with stable IDs."""
    questions = []
    seen = set()

    def add(prompt, answer, options):
        if prompt in seen:
            return
        seen.add(prompt)
        choices = list(options)
        random.shuffle(choices)
        questions.append({
            "id": start_id + len(questions),
            "question": prompt,
            "options": choices,
            "answer": answer
        })

    for item, answer in TRASH_DATA.items():
        for template in TEMPLATES:
            add(template.format(item=item), answer, CATEGORIES)

    for category in CATEGORIES:
        correct_items = [item for item, value in TRASH_DATA.items() if value == category]
        incorrect_items = [item for item, value in TRASH_DATA.items() if value != category]
        for template in [
            "Vật nào sau đây thuộc nhóm {category}?",
            "Trong các vật sau, đâu là ví dụ của {category}?"
        ]:
            item = random.choice(correct_items)
            wrong = random.sample(incorrect_items, 3)
            add(template.format(category=category), item, [item] + wrong)

    for item, correct, wrong in ACTIONS:
        add(f"Cách xử lý phù hợp với {item} là gì?", correct, [correct] + wrong)
        add(f"Bạn nên làm gì với {item}?", correct, [correct] + wrong)

    return questions
