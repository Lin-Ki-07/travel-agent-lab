// 表单状态与校验。所有字段保持字符串，与 POST /api/plans 的契约一致。
// 后端仍会做完整校验；这里只提前拦截明显的必填与格式问题。

export interface TripFormValues {
  destination: string
  start_date: string
  durationMode: 'days' | 'end_date'
  days: string
  end_date: string
  travelers: string
  budget_cny: string
  preferences: string
}

export const emptyTripForm: TripFormValues = {
  destination: '',
  start_date: '',
  durationMode: 'days',
  days: '',
  end_date: '',
  travelers: '',
  budget_cny: '',
  preferences: '',
}

export type TripFormErrors = Partial<Record<keyof TripFormValues, string>>

const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/
const INT_PATTERN = /^\d+$/

function isValidDate(text: string): boolean {
  if (!DATE_PATTERN.test(text)) return false
  const date = new Date(`${text}T00:00:00Z`)
  return !Number.isNaN(date.getTime()) && date.toISOString().slice(0, 10) === text
}

export function validateTripForm(values: TripFormValues): TripFormErrors {
  const errors: TripFormErrors = {}

  if (!values.destination.trim()) {
    errors.destination = '请填写目的地'
  }

  if (!values.start_date) {
    errors.start_date = '请填写出发日期'
  } else if (!isValidDate(values.start_date)) {
    errors.start_date = '出发日期应为 YYYY-MM-DD 的有效日期'
  }

  if (values.durationMode === 'days') {
    const days = values.days.trim()
    if (!days) {
      errors.days = '请填写旅行天数'
    } else if (!INT_PATTERN.test(days) || Number(days) < 1) {
      errors.days = '旅行天数必须是大于等于 1 的整数'
    }
  } else {
    if (!values.end_date) {
      errors.end_date = '请填写结束日期'
    } else if (!isValidDate(values.end_date)) {
      errors.end_date = '结束日期应为 YYYY-MM-DD 的有效日期'
    } else if (
      isValidDate(values.start_date) &&
      values.end_date < values.start_date
    ) {
      errors.end_date = '结束日期不能早于出发日期'
    }
  }

  const travelers = values.travelers.trim()
  if (travelers && (!INT_PATTERN.test(travelers) || Number(travelers) < 1)) {
    errors.travelers = '同行人数必须是大于等于 1 的整数'
  }

  const budget = values.budget_cny.trim()
  if (budget && !INT_PATTERN.test(budget)) {
    errors.budget_cny = '预算必须是非负整数（人民币元）'
  }

  return errors
}

// 生成请求体：天数与结束日期只发送选中的一项，另一项为空字符串。
// 可选字段留空时发送空字符串，后端会按默认值处理。
export function toRequestBody(values: TripFormValues): Record<string, string> {
  const usesDays = values.durationMode === 'days'
  return {
    destination: values.destination.trim(),
    start_date: values.start_date,
    days: usesDays ? values.days.trim() : '',
    end_date: usesDays ? '' : values.end_date,
    travelers: values.travelers.trim(),
    budget_cny: values.budget_cny.trim(),
    preferences: values.preferences.trim(),
  }
}
