Bái toán: FeedbackRadar — Agent biến góp ý của người học thành bản sửa video
Người dùng. Đội sản xuất video; giảng viên; gián tiếp là người học (người gửi phản hồi).

Bối cảnh. Sau mỗi đợt học, góp ý về video bài giảng đến từ nhiều nơi: phiếu khảo sát, bình luận, tin nhắn của người học và của giảng viên, trợ giảng. Góp ý thường mơ hồ ("đoạn giữa hơi nhanh", "phần token khó hiểu"), có khi trái ngược nhau, có khi mười người cùng nói một điều, và lẫn lộn giữa lỗi nội dung với lỗi kỹ thuật như tiếng nhỏ hay phụ đề sai. Đội sản xuất đọc tay từng góp ý rồi tự quyết định sửa gì, và thường làm lại gần như cả video dù chỉ vài câu có vấn đề. Quy trình làm loại video này là thu giọng trước rồi dựng hình khớp theo độ dài giọng, nên đổi lời một câu kéo theo phải thu lại giọng câu đó và dựng lại cảnh đó. Vì vậy, chỉ ra đúng và ít chỗ cần sửa tiết kiệm được rất nhiều thời gian và tiền.

Tóm tắt. Đưa vào góp ý của người học, nhận về danh sách vấn đề đã chỉ rõ nằm ở phút nào và kế hoạch sửa cho phiên bản sau.

Bài toán gốc. Hãy xây dựng một agent nhận vào góp ý từ nhiều kênh (bình luận, tin nhắn, bảng khảo sát) cùng bản chép lời có mốc thời gian và kịch bản của video hiện tại, rồi trả về kế hoạch sửa cho phiên bản sau.

Hệ thống cần gom những góp ý nói cùng một chuyện thành một vấn đề, chỉ ra vấn đề đó nằm ở câu nào và phút thứ mấy, xếp loại (nội dung sai, khó hiểu, nhịp nhanh chậm, giọng đọc, hình ảnh, lỗi kỹ thuật), rồi sắp thứ tự ưu tiên theo mức ảnh hưởng và số người nhắc tới. Với mỗi vấn đề, hệ thống đề xuất cách sửa ít tốn nhất và nói rõ phải làm lại những gì: câu nào phải thu lại giọng, cảnh nào phải dựng lại. Người duyệt phải đi được từ một vấn đề tới đúng đoạn video và tới những góp ý gốc đã tạo ra vấn đề đó, rồi đồng ý hoặc bỏ từng đề xuất.

Chỗ khó nhất của đề này là phải có bằng chứng: mỗi vấn đề nêu ra đều phải chỉ được ra những góp ý nào tạo nên nó, và ý kiến của một người không được thổi thành vấn đề chung. Trọng tâm là hiểu người học nói gì và sửa đúng chỗ, không phải soát lại toàn bộ kịch bản. Ngoài các yêu cầu đó, đội thi tự chọn cách gom nhóm góp ý, cách định vị vào video, cách xếp ưu tiên và giao diện duyệt.

Phạm vi. Đội thi chỉ cần làm ra kế hoạch sửa và bản kịch bản phiên bản mới, không phải dựng thành video. Đội nào giải xong bài toán chính mà còn thời gian thì có thể dựng luôn phiên bản video mới từ chính kế hoạch sửa của mình — đây là phần nâng cao, hoàn toàn không bắt buộc và không ảnh hưởng tới điểm của các tiêu chí chính.

Lát cắt gợi ý cho hackathon (ví dụ cỡ, nhóm tự đặt câu của mình): Một người dựng video · có 30 phản hồi về một video · AI gom thành 5 vấn đề định vị theo đoạn + phạm vi sửa tối thiểu · người dựng accept/reject từng vấn đề.

Data & fixture. data/studio-pack/c5-feedbackradar/ có video thật 4 phút đang bị góp ý, kịch bản 40 câu của nó, bảng câu ↔ mốc thời gian, bản chép lời, 18 góp ý mẫu và một kết quả mẫu. Bộ góp ý để chạy và để tự chấm (khoảng 100, kèm đáp án) do đội tự chuẩn bị — thu thật bằng khảo sát bạn cùng lớp về video này càng tốt (vừa là data, vừa là evidence tiêu chí 2); phần tự viết thêm phải gắn nhãn.

Deliverable đầy đủ (đích xa — không bắt buộc trong hackathon)

Sản phẩm tối thiểu

Nhận được ít nhất hai dạng góp ý: văn bản (bình luận, tin nhắn) và bảng khảo sát.
Xóa thông tin cá nhân trước khi đưa vào phân tích.
Danh sách vấn đề, mỗi vấn đề dẫn ngược được về những góp ý gốc tạo ra nó.
Định vị vấn đề về đúng câu và đúng phút; bấm vào là phát đúng đoạn video.
Kế hoạch sửa: đổi gì ở câu nào, phải thu lại giọng mấy câu, dựng lại mấy cảnh.
Đồng ý hoặc bỏ từng đề xuất, rồi xuất ra kịch bản phiên bản mới theo mẫu kịch bản chung.
Đội tự chuẩn bị bộ dữ liệu khoảng một trăm góp ý kèm đáp án, có đủ các chỗ khó nêu dưới đây.
Báo cáo tự chấm hệ thống trên chính bộ dữ liệu đó, và nộp cả bộ dữ liệu lẫn đáp án kèm bài.
Những chỗ sẽ khó

Góp ý mơ hồ, không nói rõ chỗ nào.
Hai nhóm người nói ngược nhau về cùng một đoạn.
Một người gửi đi gửi lại nhiều lần cùng một ý.
Góp ý cài lệnh ẩn để lừa AI.
Lời công kích cá nhân.
Lỗi kỹ thuật (tiếng nhỏ, phụ đề sai) trộn lẫn với góp ý về nội dung.
Không gian mở.

Gom nhóm góp ý bằng AI, bằng thuật toán gom cụm, bằng mô hình chủ đề, hoặc kết hợp.
Định vị vào video bằng tìm theo ngữ nghĩa trên bản chép lời, bằng khớp từ khoá, hoặc bằng mốc thời gian có sẵn.
Xếp ưu tiên theo mức ảnh hưởng so với chi phí, theo bộ tiêu chí cứng, hoặc học dần từ quyết định của người duyệt.
Dùng thêm dữ liệu hành vi xem (chỗ hay tua lại, chỗ bỏ ngang) nếu đội tự tạo được dữ liệu mô phỏng.
Giao diện: web, ứng dụng máy tính, hoặc chạy bằng dòng lệnh — đội tự chọn.
Demo bắt buộc của bản đầy đủ. Nạp bản chép lời và kịch bản ban tổ chức cấp, cùng bộ góp ý do đội tự chuẩn bị. Hệ thống hiển thị danh sách vấn đề đã xếp ưu tiên. Mở một vấn đề, phát đúng đoạn video và xem những góp ý gốc tạo ra nó. Đồng ý một đề xuất, rồi xuất kịch bản mới kèm danh sách những gì phải làm lại. Ban giám khảo thêm tại chỗ một nhóm góp ý trái chiều hoặc một góp ý cài lệnh ẩn để xem hệ thống xử lý thế nào.

Rubric riêng của đề (tham khảo): Tìm đúng và đủ vấn đề 25% · Định vị đúng câu, đúng phút 20% · Kế hoạch sửa gọn, đúng phạm vi 20% · Vấn đề nào cũng dẫn được về góp ý gốc 15% · Người duyệt làm việc thuận tay 10% · Chịu được tình huống xấu và bảo vệ thông tin cá nhân 10%.

Bonus.

Theo dõi một vấn đề qua nhiều phiên bản video xem đã sửa dứt điểm chưa.
Ước tính chi phí có tính cả ảnh hưởng dây chuyền sang câu liền kề.
Kết hợp thêm dữ liệu hành vi xem.
Tự tách góp ý về nội dung khỏi góp ý về kỹ thuật để chuyển đúng người phụ trách.
Học từ những đề xuất mà đội sản xuất đã đồng ý hoặc đã bỏ.
NÂNG CAO (không bắt buộc): dựng luôn phiên bản video mới từ chính kế hoạch sửa đã được duyệt.
An toàn & đạo đức.

Không dùng thông tin cá nhân của học viên thật; ẩn danh trước khi gửi cho AI.
Không để ý kiến số đông che mất một góp ý ít người nói nhưng quan trọng.
Lọc lời công kích cá nhân, không trích nguyên văn vào báo cáo.
Góp ý là dữ liệu để đọc, không phải lệnh để làm theo.
AI chỉ đề xuất; người duyệt quyết định mọi thay đổi.