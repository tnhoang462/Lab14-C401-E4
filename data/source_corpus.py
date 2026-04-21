"""
Source corpus — tập tài liệu nền cho synthetic data generation.

Mỗi document có `id` ổn định để có thể dùng làm `ground_truth_ids`
cho Retrieval Evaluation (Hit Rate / MRR).

Domain: Nội quy & hỗ trợ kỹ thuật nội bộ của một công ty giả định ("AcmeCorp").
"""

from typing import List, Dict

CORPUS: List[Dict] = [
    {
        "id": "doc_001",
        "title": "Chính sách đổi mật khẩu",
        "topic": "account_security",
        "content": (
            "Nhân viên AcmeCorp bắt buộc đổi mật khẩu định kỳ 90 ngày một lần. "
            "Mật khẩu mới phải có tối thiểu 12 ký tự, bao gồm chữ hoa, chữ thường, "
            "số và ký tự đặc biệt. Hệ thống không cho phép tái sử dụng 5 mật khẩu gần nhất. "
            "Khi quên mật khẩu, nhân viên truy cập portal self-service tại "
            "https://sso.acmecorp.internal/reset và xác minh qua email công ty + OTP điện thoại."
        ),
    },
    {
        "id": "doc_002",
        "title": "Xác thực đa yếu tố (MFA)",
        "topic": "account_security",
        "content": (
            "AcmeCorp bật MFA mặc định cho toàn bộ tài khoản nhân viên từ 2024-01-01. "
            "Các phương thức được chấp nhận gồm: ứng dụng Authenticator (Google/Microsoft), "
            "YubiKey phần cứng, và SMS OTP (chỉ backup). "
            "Không cho phép tắt MFA kể cả với tài khoản service — phải xin đặc cách từ IT Security."
        ),
    },
    {
        "id": "doc_003",
        "title": "Chính sách làm việc từ xa",
        "topic": "remote_work",
        "content": (
            "Nhân viên full-time được làm việc từ xa tối đa 3 ngày mỗi tuần. "
            "Ngày bắt buộc đến văn phòng là Thứ Ba và Thứ Năm. "
            "Nhân viên thuộc nhóm Sales và Customer Success áp dụng lịch linh hoạt theo thỏa thuận với manager. "
            "Khi làm việc từ xa, bắt buộc kết nối qua VPN AcmeCorp-Global."
        ),
    },
    {
        "id": "doc_004",
        "title": "Chính sách ngày nghỉ phép",
        "topic": "hr_leave",
        "content": (
            "Nhân viên full-time được hưởng 15 ngày phép có lương mỗi năm, cộng thêm "
            "1 ngày sinh nhật và 5 ngày nghỉ bệnh không cần chứng nhận y tế. "
            "Phép chưa dùng trong năm được rollover tối đa 5 ngày sang năm sau. "
            "Yêu cầu nghỉ phải được gửi qua Workday ít nhất 7 ngày trước ngày nghỉ (trừ nghỉ bệnh khẩn)."
        ),
    },
    {
        "id": "doc_005",
        "title": "Chính sách chi phí công tác",
        "topic": "expense",
        "content": (
            "Công tác trong nước: per diem 800.000đ/ngày cho ăn uống, khách sạn tối đa 1.500.000đ/đêm. "
            "Công tác quốc tế: per diem theo mức của từng quốc gia trong bảng đính kèm, khách sạn tối đa 180 USD/đêm. "
            "Mọi hóa đơn phải được chụp và upload vào hệ thống Expensify trong vòng 14 ngày sau chuyến công tác. "
            "Không hoàn tiền mini-bar, đồ uống có cồn, và giải trí cá nhân."
        ),
    },
    {
        "id": "doc_006",
        "title": "Chính sách bảo mật thiết bị (BYOD / Company laptop)",
        "topic": "device_security",
        "content": (
            "Laptop công ty phải bật full-disk encryption (FileVault trên Mac, BitLocker trên Windows). "
            "AcmeCorp cài sẵn MDM Jamf/Intune để quản lý thiết bị. "
            "Thiết bị cá nhân (BYOD) chỉ được phép truy cập email và Slack qua các app được approve, "
            "không được truy cập source code hoặc dữ liệu khách hàng. "
            "Mất thiết bị phải báo IT Security trong vòng 4 giờ."
        ),
    },
    {
        "id": "doc_007",
        "title": "Quy trình onboarding nhân viên mới",
        "topic": "onboarding",
        "content": (
            "Ngày đầu tiên: nhận laptop, setup tài khoản SSO, ký NDA và thỏa thuận lao động điện tử. "
            "Tuần 1: hoàn thành khóa Security Awareness Training bắt buộc. "
            "Tuần 2-4: bắt buộc 1:1 với manager mỗi tuần, hoàn thành Compliance 101. "
            "Cuối tháng 1: review probation milestone với HR Business Partner."
        ),
    },
    {
        "id": "doc_008",
        "title": "Chính sách Data Classification",
        "topic": "data_security",
        "content": (
            "AcmeCorp phân loại dữ liệu thành 4 nhóm: Public, Internal, Confidential, Restricted. "
            "Dữ liệu Restricted (PII khách hàng, dữ liệu tài chính chưa công bố) chỉ được xử lý trong "
            "môi trường production có tag 'restricted' và truy cập cần approval của Data Protection Officer. "
            "Cấm upload dữ liệu Confidential trở lên lên các dịch vụ AI bên ngoài như ChatGPT, Gemini public."
        ),
    },
    {
        "id": "doc_009",
        "title": "Chính sách sử dụng AI/LLM nội bộ",
        "topic": "ai_policy",
        "content": (
            "Nhân viên được khuyến khích dùng AcmeCorp Copilot (Gemini Enterprise) cho công việc hằng ngày. "
            "Không được dán source code chứa thông tin nhạy cảm, khóa API, hoặc dữ liệu khách hàng vào các "
            "công cụ AI public. Model Risk Committee phê duyệt mọi use case AI ra sản phẩm. "
            "Mọi output AI dùng trong tài liệu khách hàng phải có human-in-the-loop review."
        ),
    },
    {
        "id": "doc_010",
        "title": "Quy trình báo cáo sự cố bảo mật",
        "topic": "incident_response",
        "content": (
            "Mọi nghi ngờ sự cố bảo mật (phishing, rò rỉ dữ liệu, mất thiết bị) báo ngay qua "
            "kênh Slack #security-incident hoặc email security@acmecorp.com. "
            "SLA phản hồi của Security Team: 15 phút trong giờ hành chính, 60 phút ngoài giờ. "
            "Nhân viên KHÔNG được tự ý thử khai thác hoặc xóa bằng chứng — giữ nguyên hiện trạng."
        ),
    },
    {
        "id": "doc_011",
        "title": "Chính sách đánh giá hiệu suất (Performance Review)",
        "topic": "hr_performance",
        "content": (
            "Chu kỳ đánh giá: 2 lần/năm vào tháng 6 và tháng 12. "
            "Thang điểm: Below Expectations / Meets / Exceeds / Outstanding. "
            "Nhân viên phải hoàn thành self-review + peer feedback (≥3 peers) trước deadline. "
            "Manager chốt rating trong Calibration Meeting — không có rating mặc định."
        ),
    },
    {
        "id": "doc_012",
        "title": "Chính sách lương thưởng & bonus",
        "topic": "compensation",
        "content": (
            "Lương được trả vào ngày 5 hằng tháng qua tài khoản Vietcombank hoặc Techcombank. "
            "Annual bonus tối đa 3 tháng lương, dựa trên performance rating và company performance multiplier. "
            "Bonus được trả vào tháng 3 năm sau. "
            "Nhân viên nghỉ việc trước ngày trả bonus không đủ điều kiện nhận bonus năm đó."
        ),
    },
    {
        "id": "doc_013",
        "title": "Quyền lợi bảo hiểm sức khỏe",
        "topic": "benefits",
        "content": (
            "AcmeCorp cung cấp gói bảo hiểm Bảo Việt An Gia cấp độ Platinum cho nhân viên, "
            "cộng thêm bảo hiểm cho vợ/chồng và tối đa 2 con dưới 18 tuổi. "
            "Mức hoàn trả nội trú: 100% trong hạn mức 500 triệu/năm. "
            "Khám định kỳ miễn phí hằng năm tại Vinmec, Family Medical Practice, hoặc FV Hospital."
        ),
    },
    {
        "id": "doc_014",
        "title": "Quy trình xin nghỉ việc & bàn giao",
        "topic": "offboarding",
        "content": (
            "Nhân viên phải thông báo bằng văn bản tối thiểu 30 ngày trước ngày nghỉ với role IC, "
            "45 ngày với role Manager trở lên. "
            "Ngày cuối cùng: trả lại laptop, YubiKey, thẻ ra vào, và hoàn tất offboarding checklist trên BambooHR. "
            "Lương tháng cuối + phép tồn quy đổi được chi trả trong vòng 14 ngày làm việc."
        ),
    },
    {
        "id": "doc_015",
        "title": "Code of Conduct & chính sách chống quấy rối",
        "topic": "code_of_conduct",
        "content": (
            "AcmeCorp zero-tolerance với mọi hành vi quấy rối, phân biệt đối xử hoặc bắt nạt. "
            "Báo cáo ẩn danh qua EthicsPoint Hotline 24/7. Mọi báo cáo được điều tra bởi bên thứ 3 độc lập. "
            "Trả đũa người báo cáo là vi phạm nghiêm trọng có thể dẫn tới sa thải ngay."
        ),
    },
    {
        "id": "doc_016",
        "title": "Chính sách đào tạo & phát triển",
        "topic": "learning_development",
        "content": (
            "Mỗi nhân viên được cấp ngân sách L&D 15.000.000đ/năm cho khóa học, sách, chứng chỉ. "
            "Các chứng chỉ AWS/GCP/Azure được hoàn 100% phí thi lần đầu. "
            "Cần pre-approval của manager nếu khoản chi > 3.000.000đ. "
            "Ngân sách không dùng hết không được rollover sang năm kế tiếp."
        ),
    },
    {
        "id": "doc_017",
        "title": "Chính sách open source contribution",
        "topic": "engineering_policy",
        "content": (
            "Nhân viên engineering được khuyến khích đóng góp open source ngoài giờ làm việc. "
            "Các dự án liên quan đến domain công ty (fintech, AI infra) cần đăng ký với Legal trước. "
            "Tuyệt đối không đưa code nội bộ AcmeCorp lên repo public. "
            "Tên tác giả có thể dùng email cá nhân, không bắt buộc gắn tên công ty."
        ),
    },
    {
        "id": "doc_018",
        "title": "Chính sách chi tiêu Cloud (FinOps)",
        "topic": "engineering_policy",
        "content": (
            "Mọi service mới trên AWS/GCP phải có tag 'owner', 'cost-center', 'env'. "
            "Ngân sách hằng tháng của team được alert khi đạt 80% và tự động block scaling mới khi đạt 100%. "
            "Resource idle > 7 ngày trong môi trường dev sẽ bị tắt tự động bởi FinOps Bot. "
            "Các khoản chi > 50.000 USD/tháng cần approval của CFO."
        ),
    },
    {
        "id": "doc_019",
        "title": "Quy định sử dụng mạng xã hội",
        "topic": "code_of_conduct",
        "content": (
            "Nhân viên có quyền tự do ngôn luận trên mạng xã hội cá nhân, "
            "nhưng không được đại diện cho AcmeCorp khi chưa được ủy quyền chính thức. "
            "Cấm chia sẻ thông tin Confidential/Restricted, hình ảnh văn phòng có whiteboard, hoặc "
            "bình luận về khách hàng. Khi có tranh cãi công khai liên quan công ty, liên hệ bộ phận PR."
        ),
    },
    {
        "id": "doc_020",
        "title": "Chính sách parental leave",
        "topic": "hr_leave",
        "content": (
            "Mẹ sinh: 6 tháng nghỉ có lương đầy đủ (theo luật Việt Nam) + 1 tháng AcmeCorp top-up. "
            "Bố: 14 ngày nghỉ có lương, có thể chia thành nhiều đợt trong 6 tháng đầu sau sinh. "
            "Nhận con nuôi: áp dụng tương đương chế độ sinh, bắt đầu từ ngày nhận con. "
            "Chế độ flexible return-to-work 50%-80%-100% trong 3 tháng đầu quay lại."
        ),
    },
]


def get_corpus() -> List[Dict]:
    """Trả về toàn bộ corpus."""
    return CORPUS


def get_doc_by_id(doc_id: str) -> Dict:
    for d in CORPUS:
        if d["id"] == doc_id:
            return d
    raise KeyError(f"Doc {doc_id} không tồn tại trong corpus")


def get_all_ids() -> List[str]:
    return [d["id"] for d in CORPUS]


if __name__ == "__main__":
    print(f"Corpus có {len(CORPUS)} tài liệu")
    for d in CORPUS:
        print(f"  {d['id']}: {d['title']}  [{d['topic']}]")
