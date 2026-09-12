import type { WorkflowRun, DemoScenarioId } from './types';

export const mockScenarios: Record<DemoScenarioId, WorkflowRun> = {
  // Scenario A: Company-only run
  COMPANY_ONLY: {
    runId: 'run-company-only-2024',
    createdAt: '2026-09-12T09:15:00+07:00',
    question: 'ROE của TCB thay đổi thế nào trong năm 2024?',
    scopeSignature: 'TCB · Q1–Q4/2024 · ROE',
    datasetName: 'Ngân hàng Việt Nam 2024',
    orchestrator: {
      planObjective: 'Phân tích biến động tỷ suất sinh lời trên vốn chủ sở hữu (ROE) của Techcombank qua 4 quý năm 2024.',
      activeSpecialistIds: ['company'],
      overallStatus: 'RUNNING',
      overallStatusLabel: 'Đang phân tích',
      planningRationale: 'Yêu cầu phân tích đơn mục tiêu tập trung vào một doanh nghiệp. Hệ thống chỉ kích hoạt Chuyên gia Doanh nghiệp, bỏ qua Nhóm tham chiếu và Vĩ mô để tối ưu tài nguyên và độ chính xác.',
      reviewSummary: 'Chờ nhận kết quả từ Chuyên gia Doanh nghiệp để tiến hành đối soát dẫn chứng báo cáo tài chính.'
    },
    specialists: [
      {
        id: 'company',
        name: 'Phân tích Doanh nghiệp',
        roleDescription: 'Bóc tách và tính toán các tỷ số tài chính từ BCTC Techcombank',
        targetEntity: 'TCB',
        status: 'ANALYZING',
        statusLabel: 'Đang phân tích',
        currentActivityDescription: 'Đang đọc dữ liệu ROE của TCB cho Q1–Q4/2024 từ BCTC kiểm toán.',
        assignedTask: 'Tính toán ROE từng quý và lũy kế năm 2024 của Ngân hàng Kỹ thương (TCB), đối chiếu với vốn chủ sở hữu bình quân.',
        observableActivities: [
          {
            id: 'act-1',
            timestamp: '09:15:05',
            action: 'Đọc dữ liệu lợi nhuận sau thuế và VCSH bình quân',
            dataSource: 'Báo cáo tài chính hợp nhất kiểm toán 2024 (TCB)',
            status: 'COMPLETED'
          },
          {
            id: 'act-2',
            timestamp: '09:15:12',
            action: 'Tính toán tỷ số ROE từng quý: Q1 (4.1%), Q2 (4.3%), Q3 (4.0%), Q4 (4.4%)',
            dataSource: 'Động cơ tính toán tài chính Gold',
            status: 'COMPLETED'
          },
          {
            id: 'act-3',
            timestamp: '09:15:20',
            action: 'Xác minh dẫn chứng từng ô số liệu với bảng thuyết minh',
            dataSource: 'BCTC Thuyết minh nguồn vốn và lợi nhuận',
            status: 'IN_PROGRESS'
          }
        ],
        findings: [
          {
            id: 'find-1',
            title: 'ROE lũy kế cả năm 2024 của TCB đạt 16.8%, duy trì đà hồi phục ổn định qua các quý.',
            metric: 'ROE',
            value: '16.8%',
            evidenceSource: 'BCTC hợp nhất 2024 (Kiểm toán), Thuyết minh số 28',
            confidence: 'HIGH'
          }
        ]
      }
    ]
  },

  // Scenario B: Company + Peer comparative run
  COMPANY_PEER: {
    runId: 'run-company-peer-2024',
    createdAt: '2026-09-12T09:20:00+07:00',
    question: 'TCB sinh lời tốt hơn hay kém nhóm so sánh?',
    scopeSignature: 'TCB · Q1–Q4/2024 · ROA · ROE',
    datasetName: 'Ngân hàng Việt Nam 2024',
    orchestrator: {
      planObjective: 'Đối sánh năng lực sinh lời (ROA, ROE) của Techcombank so với nhóm 5 ngân hàng tham chiếu trong năm 2024.',
      activeSpecialistIds: ['company', 'peer'],
      overallStatus: 'RUNNING',
      overallStatusLabel: 'Đang phân tích',
      planningRationale: 'Yêu cầu so sánh tương đối giữa doanh nghiệp mục tiêu và nhóm ngang hàng. Kế hoạch phân tích kích hoạt song song Chuyên gia Doanh nghiệp và Chuyên gia Nhóm tham chiếu.',
      reviewSummary: 'Đang chờ dữ liệu trung vị từ nhóm tham chiếu để đối soát với hồ sơ tài chính của TCB.'
    },
    specialists: [
      {
        id: 'company',
        name: 'Phân tích Doanh nghiệp',
        roleDescription: 'Phân tích dữ liệu tài chính nội tại của TCB',
        targetEntity: 'TCB',
        status: 'PRODUCED_FINDINGS',
        statusLabel: 'Đã tạo kết quả',
        currentActivityDescription: 'Đã hoàn tất tính toán ROA (2.3%) và ROE (16.8%) năm 2024.',
        assignedTask: 'Tính toán chuỗi chỉ số sinh lời của TCB trong cả 4 quý năm 2024 và lập hồ sơ dẫn chứng.',
        observableActivities: [
          {
            id: 'c-act-1',
            timestamp: '09:20:06',
            action: 'Thu thập bảng cân đối kế toán và KQKD 4 quý của TCB',
            dataSource: 'BCTC kiểm toán TCB 2024',
            status: 'COMPLETED'
          },
          {
            id: 'c-act-2',
            timestamp: '09:20:14',
            action: 'Tính toán ROA cả năm đạt 2.31%, ROE cả năm đạt 16.82%',
            dataSource: 'Công thức tài chính chuẩn hóa',
            status: 'COMPLETED'
          }
        ],
        findings: [
          {
            id: 'c-find-1',
            title: 'ROA của Techcombank đạt 2.31%, thuộc top biên sinh lời trên tổng tài sản cao nhất phân khúc.',
            metric: 'ROA',
            value: '2.31%',
            evidenceSource: 'Báo cáo thường niên & BCTC kiểm toán 2024 TCB',
            confidence: 'HIGH'
          },
          {
            id: 'c-find-2',
            title: 'ROE đạt 16.82%, phản ánh hiệu quả sử dụng vốn cổ đông được củng cố.',
            metric: 'ROE',
            value: '16.82%',
            evidenceSource: 'BCTC kiểm toán 2024 TCB',
            confidence: 'HIGH'
          }
        ]
      },
      {
        id: 'peer',
        name: 'Nhóm tham chiếu',
        roleDescription: 'Đối sánh dữ liệu ngang hàng với Nhóm 5 ngân hàng',
        status: 'ANALYZING',
        statusLabel: 'Đang phân tích',
        currentActivityDescription: 'Đang tổng hợp trung vị ROE (15.1%) và ROA (1.8%) của ACB, VPB, MBB, VCB.',
        assignedTask: 'Xác định phân phối và giá trị trung vị sinh lời của nhóm tham chiếu 5 ngân hàng cùng kỳ 2024.',
        observableActivities: [
          {
            id: 'p-act-1',
            timestamp: '09:20:08',
            action: 'Tải tập dữ liệu đã xác thực của nhóm 5 ngân hàng (ACB, TCB, VPB, MBB, VCB)',
            dataSource: 'Kho dữ liệu Gold Snapshot v0.9',
            status: 'COMPLETED'
          },
          {
            id: 'p-act-2',
            timestamp: '09:20:18',
            action: 'Tính toán trung vị ngành: ROE trung vị 15.1%, ROA trung vị 1.82%',
            dataSource: 'Mô-đun đối sánh thống kê',
            status: 'IN_PROGRESS'
          }
        ],
        findings: [
          {
            id: 'p-find-1',
            title: 'Trung vị ROE nhóm tham chiếu đạt 15.1%; TCB vượt trung vị 1.7 điểm phần trăm.',
            metric: 'ROE Benchmark',
            value: '15.1%',
            evidenceSource: 'Tập dữ liệu chuẩn hóa 5 ngân hàng niêm yết 2024',
            confidence: 'HIGH'
          }
        ]
      }
    ]
  },

  // Scenario C: Targeted Revision example (Key thesis capability)
  TARGETED_REVISION: {
    runId: 'run-targeted-revision-2024',
    createdAt: '2026-09-12T09:25:00+07:00',
    question: 'So sánh chất lượng tài sản và tỷ lệ bao phủ nợ xấu của TCB với nhóm tham chiếu năm 2024',
    scopeSignature: 'TCB · Q1–Q4/2024 · NPL · Coverage',
    datasetName: 'Ngân hàng Việt Nam 2024',
    orchestrator: {
      planObjective: 'So sánh tỷ lệ nợ xấu (NPL) và tỷ lệ bao phủ nợ xấu (LLR/Coverage) của TCB so với nhóm tham chiếu 2024.',
      activeSpecialistIds: ['company', 'peer'],
      overallStatus: 'REVISING',
      overallStatusLabel: 'Đang hiệu chỉnh',
      planningRationale: 'Yêu cầu đối sánh rủi ro tín dụng. Chuyên gia Doanh nghiệp đã được nghiệm thu. Điều phối phát hiện sai lệch kỳ đối sánh ở Chuyên gia Nhóm tham chiếu và chỉ định hiệu chỉnh khoanh vùng.',
      reviewSummary: 'Điều phối phát hiện: Số liệu Coverage của nhóm tham chiếu sử dụng kỳ Q3 trong khi số liệu TCB là Q4/2024. Yêu cầu tính lại chuẩn hóa cùng kỳ Q4.',
      revisionRound: 1,
      totalRevisionsCount: 1
    },
    specialists: [
      {
        id: 'company',
        name: 'Phân tích Doanh nghiệp',
        roleDescription: 'Phân tích chỉ tiêu chất lượng tài sản nội tại TCB',
        targetEntity: 'TCB',
        status: 'COMPLETED',
        statusLabel: 'Đã hoàn tất',
        currentActivityDescription: 'Kết quả đã được Điều phối nghiệm thu (NPL: 1.19%, Coverage: 103%).',
        assignedTask: 'Xác định tỷ lệ nợ xấu và trích lập dự phòng rủi ro của Techcombank tại thời điểm kết thúc Q4/2024.',
        observableActivities: [
          {
            id: 'rev-c-1',
            timestamp: '09:25:04',
            action: 'Thu thập số dư nợ nhóm 3-5 và trích lập dự phòng rủi ro',
            dataSource: 'BCTC hợp nhất kiểm toán TCB 2024 (Thuyết minh 10)',
            status: 'COMPLETED'
          },
          {
            id: 'rev-c-2',
            timestamp: '09:25:15',
            action: 'Nghiệm thu: NPL 1.19%, Coverage 103.4% - Dẫn chứng hợp lệ',
            dataSource: 'Kiểm tra chất lượng Điều phối',
            status: 'COMPLETED'
          }
        ],
        findings: [
          {
            id: 'rf-c-1',
            title: 'Tỷ lệ nợ xấu (NPL) của TCB kiểm soát ở mức 1.19% tại cuối năm 2024.',
            metric: 'NPL',
            value: '1.19%',
            evidenceSource: 'BCTC kiểm toán 2024 TCB',
            confidence: 'HIGH'
          },
          {
            id: 'rf-c-2',
            title: 'Tỷ lệ bao phủ nợ xấu (LLR) đạt 103.4%, đảm bảo đệm dự phòng trên 100%.',
            metric: 'Coverage',
            value: '103.4%',
            evidenceSource: 'BCTC kiểm toán 2024 TCB',
            confidence: 'HIGH'
          }
        ]
      },
      {
        id: 'peer',
        name: 'Nhóm tham chiếu',
        roleDescription: 'Đối sánh rủi ro với nhóm 5 ngân hàng',
        status: 'REVISING',
        statusLabel: 'Đang hiệu chỉnh · Vòng 1/2',
        currentActivityDescription: 'Đang tính toán lại tỷ lệ bao phủ nợ xấu theo số liệu Q4/2024 của nhóm tham chiếu.',
        assignedTask: 'Tính toán tỷ lệ nợ xấu trung vị và bao phủ nợ xấu trung vị của nhóm 5 ngân hàng tại Q4/2024.',
        observableActivities: [
          {
            id: 'rev-p-1',
            timestamp: '09:25:08',
            action: 'Tính toán ban đầu bị từ chối: Phát hiện dữ liệu ACB và VPB bị lệch kỳ Q3/2024',
            dataSource: 'Cơ chế kiểm soát chất lượng phản biện',
            status: 'COMPLETED'
          },
          {
            id: 'rev-p-2',
            timestamp: '09:25:25',
            action: 'Tải lại dữ liệu báo cáo tài chính Q4/2024 của toàn bộ 5 ngân hàng',
            dataSource: 'BCTC kiểm toán năm 2024 các ngân hàng tham chiếu',
            status: 'IN_PROGRESS'
          }
        ],
        findings: [
          {
            id: 'rf-p-1',
            title: 'NPL trung vị nhóm tham chiếu năm 2024 đạt 1.45% (TCB thấp hơn mức trung vị).',
            metric: 'NPL Median',
            value: '1.45%',
            evidenceSource: 'Dữ liệu 5 ngân hàng 2024 (Đã duyệt)',
            confidence: 'HIGH'
          }
        ],
        revision: {
          iteration: 1,
          maxIterations: 2,
          orchestratorFeedback: 'Điều phối phát hiện: Chỉ tiêu bao phủ nợ xấu (Coverage) của nhóm tham chiếu chưa đồng nhất kỳ đối sánh với TCB (bị trích xuất nhầm từ Q3 thay vì Q4). Yêu cầu chuẩn hóa đúng kỳ Q4/2024.',
          status: 'IN_PROGRESS',
          resolvedNote: 'Đang cập nhật lại số dư dự phòng rủi ro Q4/2024 cho ACB và VPB.'
        }
      }
    ]
  },

  // Scenario D: Broad Analysis (3 specialists)
  BROAD_ANALYSIS: {
    runId: 'run-broad-2024',
    createdAt: '2026-09-12T09:30:00+07:00',
    question: 'So sánh chất lượng tài sản của ACB, TCB và MBB trong năm 2024 và tác động của môi trường vĩ mô.',
    scopeSignature: 'ACB · TCB · MBB · Q1–Q4/2024 · NPL · Coverage',
    datasetName: 'Ngân hàng Việt Nam 2024',
    orchestrator: {
      planObjective: 'Đánh giá toàn diện chất lượng tài sản các ngân hàng mục tiêu đặt trong môi trường chính sách tiền tệ và tương quan nhóm tham chiếu.',
      activeSpecialistIds: ['company', 'peer', 'macro'],
      overallStatus: 'SYNTHESIZING',
      overallStatusLabel: 'Đang tổng hợp',
      planningRationale: 'Yêu cầu phân tích đa chiều. Kế hoạch phân tích kích hoạt cả 3 chuyên gia: Doanh nghiệp, Nhóm tham chiếu và Bối cảnh vĩ mô.',
      reviewSummary: 'Tất cả 3 chuyên gia đã hoàn tất phát hiện có dẫn chứng. Điều phối đang tổng hợp luận điểm nhất quán cho báo cáo.',
      synthesisSummary: 'Đang liên kết tác động tăng trưởng tín dụng 15% của SBV với diễn biến nợ xấu của từng ngân hàng.'
    },
    specialists: [
      {
        id: 'macro',
        name: 'Bối cảnh Vĩ mô',
        roleDescription: 'Phân tích chính sách tiền tệ và tăng trưởng tín dụng',
        status: 'COMPLETED',
        statusLabel: 'Đã hoàn tất',
        currentActivityDescription: 'Đã cung cấp bối cảnh tăng trưởng tín dụng toàn ngành 15.08% năm 2024.',
        assignedTask: 'Tổng hợp diễn biến lãi suất điều hành và hạn mức tín dụng của Ngân hàng Nhà nước trong năm 2024.',
        observableActivities: [
          {
            id: 'm-act-1',
            timestamp: '09:30:05',
            action: 'Trích xuất văn bản chỉ đạo của NHNN về hạn mức tăng trưởng tín dụng 2024',
            dataSource: 'Cơ sở dữ liệu vĩ mô SBV',
            status: 'COMPLETED'
          }
        ],
        findings: [
          {
            id: 'm-find-1',
            title: 'Tăng trưởng tín dụng toàn hệ thống đạt 15.08%, chính sách tiền tệ duy trì nới lỏng linh hoạt.',
            metric: 'Credit Growth',
            value: '15.08%',
            evidenceSource: 'Báo cáo thống kê NHNN 2024',
            confidence: 'HIGH'
          }
        ]
      },
      {
        id: 'peer',
        name: 'Nhóm tham chiếu',
        roleDescription: 'Đối sánh nhóm ngân hàng cùng phân khúc',
        status: 'COMPLETED',
        statusLabel: 'Đã hoàn tất',
        currentActivityDescription: 'Đã hoàn tất lập bản đồ vị thế rủi ro tín dụng 5 ngân hàng.',
        assignedTask: 'Tính toán phân vị nợ xấu và bao phủ nợ xấu của nhóm tham chiếu 2024.',
        observableActivities: [
          {
            id: 'bp-act-1',
            timestamp: '09:30:10',
            action: 'Tính toán ma trận nợ xấu và phân vị nhóm ngân hàng tư nhân',
            dataSource: 'Kho dữ liệu Gold Snapshot v0.9',
            status: 'COMPLETED'
          }
        ],
        findings: [
          {
            id: 'bp-find-1',
            title: 'ACB và TCB duy trì tỷ lệ nợ xấu ở nhóm 1/3 thấp nhất trong nhóm tham chiếu.',
            metric: 'NPL Ranking',
            value: 'Top quartile',
            evidenceSource: 'Bộ chỉ số tài chính Gold 2024',
            confidence: 'HIGH'
          }
        ]
      },
      {
        id: 'company',
        name: 'Phân tích Doanh nghiệp',
        roleDescription: 'Phân tích chi tiết số liệu ACB, TCB, MBB',
        targetEntity: 'ACB, TCB, MBB',
        status: 'COMPLETED',
        statusLabel: 'Đã hoàn tất',
        currentActivityDescription: 'Đã hoàn tất đối chiếu BCTC 3 ngân hàng mục tiêu.',
        assignedTask: 'Lập báo cáo nợ nhóm 2 và nợ xấu (NPL) của ACB, TCB và MBB.',
        observableActivities: [
          {
            id: 'bc-act-1',
            timestamp: '09:30:14',
            action: 'Bóc tách nợ cần chú ý (nhóm 2) và nợ xấu (nhóm 3-5)',
            dataSource: 'BCTC kiểm toán 2024 của ACB, TCB, MBB',
            status: 'COMPLETED'
          }
        ],
        findings: [
          {
            id: 'bc-find-1',
            title: 'ACB kiểm soát NPL ở mức 1.21%, TCB đạt 1.19%, MBB đạt 1.58%.',
            metric: 'NPL Comparison',
            value: '1.19% - 1.58%',
            evidenceSource: 'BCTC hợp nhất kiểm toán 2024',
            confidence: 'HIGH'
          }
        ]
      }
    ]
  }
};
