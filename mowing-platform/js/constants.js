// Status labels and constants / 状态标签和常量
const statusLabels = {
  pending_review: "待平台确认",
  quoted: "已报价",
  accepted_by_customer: "客户已确认",
  assigned: "已派单",
  accepted_by_worker: "服务商已接单",
  in_service: "服务中",
  pending_quality_review: "待质量审核",
  completed: "已完成",
  exception_open: "异常处理中",
  cancelled: "已取消",
};

const workerApprovalLabels = {
  approved: "已审核",
  probation: "观察中",
  pending_info: "资料待补充",
};

const settlementLabels = {
  pending: "待结算",
  settled: "已结算",
};

const paymentLabels = {
  unpaid: "未收款",
  pending: "待收款",
  paid: "已收款",
  waived: "免收",
};

const priorityLabels = {
  low: "低优先级",
  normal: "常规",
  high: "优先处理",
  urgent: "紧急",
};
