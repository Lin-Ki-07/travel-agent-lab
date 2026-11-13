import { useState, type FormEvent } from 'react'
import { createPlan, PlanApiError, type CreatePlanResponse } from './api'
import {
  emptyTripForm,
  toRequestBody,
  validateTripForm,
  type TripFormErrors,
  type TripFormValues,
} from './tripRequest'

interface TripFormProps {
  onGenerated: (result: CreatePlanResponse) => void
  // 初始值由父组件提供（例如自然语言解析的结果）；变化时父组件应通过 key 重新挂载表单。
  initialValues?: TripFormValues
}

export default function TripForm({ onGenerated, initialValues }: TripFormProps) {
  const [values, setValues] = useState<TripFormValues>(initialValues ?? emptyTripForm)
  const [errors, setErrors] = useState<TripFormErrors>({})
  const [loading, setLoading] = useState(false)
  const [apiError, setApiError] = useState<PlanApiError | null>(null)

  function update<K extends keyof TripFormValues>(key: K, value: TripFormValues[K]) {
    setValues((prev) => ({ ...prev, [key]: value }))
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (loading) return

    const fieldErrors = validateTripForm(values)
    setErrors(fieldErrors)
    setApiError(null)
    if (Object.keys(fieldErrors).length > 0) return

    setLoading(true)
    try {
      const result = await createPlan(toRequestBody(values))
      onGenerated(result)
    } catch (error) {
      setApiError(
        error instanceof PlanApiError
          ? error
          : new PlanApiError('生成行程时发生未知错误。', null),
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <form className="card trip-form" onSubmit={handleSubmit} noValidate>
      <h3>旅行需求</h3>

      <label className="field">
        <span>目的地 <em>*</em></span>
        <input
          value={values.destination}
          onChange={(e) => update('destination', e.target.value)}
          placeholder="例如：杭州"
          aria-invalid={Boolean(errors.destination)}
        />
        {errors.destination && <small className="field-error">{errors.destination}</small>}
      </label>

      <label className="field">
        <span>出发日期 <em>*</em></span>
        <input
          type="date"
          value={values.start_date}
          onChange={(e) => update('start_date', e.target.value)}
          aria-invalid={Boolean(errors.start_date)}
        />
        {errors.start_date && <small className="field-error">{errors.start_date}</small>}
      </label>

      <fieldset className="field">
        <legend>行程长度 <em>*</em>（二选一）</legend>
        <div className="inline-options">
          <label>
            <input
              type="radio"
              name="durationMode"
              checked={values.durationMode === 'days'}
              onChange={() => update('durationMode', 'days')}
            />
            天数
          </label>
          <label>
            <input
              type="radio"
              name="durationMode"
              checked={values.durationMode === 'end_date'}
              onChange={() => update('durationMode', 'end_date')}
            />
            结束日期
          </label>
        </div>
        {values.durationMode === 'days' ? (
          <input
            inputMode="numeric"
            value={values.days}
            onChange={(e) => update('days', e.target.value)}
            placeholder="例如：2"
            aria-label="旅行天数"
            aria-invalid={Boolean(errors.days)}
          />
        ) : (
          <input
            type="date"
            value={values.end_date}
            onChange={(e) => update('end_date', e.target.value)}
            aria-label="结束日期"
            aria-invalid={Boolean(errors.end_date)}
          />
        )}
        {(errors.days || errors.end_date) && (
          <small className="field-error">{errors.days ?? errors.end_date}</small>
        )}
      </fieldset>

      <label className="field">
        <span>同行人数</span>
        <input
          inputMode="numeric"
          value={values.travelers}
          onChange={(e) => update('travelers', e.target.value)}
          placeholder="留空默认为 1"
          aria-invalid={Boolean(errors.travelers)}
        />
        {errors.travelers && <small className="field-error">{errors.travelers}</small>}
      </label>

      <label className="field">
        <span>全程预算（元，所有同行者合计）</span>
        <input
          inputMode="numeric"
          value={values.budget_cny}
          onChange={(e) => update('budget_cny', e.target.value)}
          placeholder="可留空"
          aria-invalid={Boolean(errors.budget_cny)}
        />
        {errors.budget_cny && <small className="field-error">{errors.budget_cny}</small>}
      </label>

      <label className="field">
        <span>偏好</span>
        <input
          value={values.preferences}
          onChange={(e) => update('preferences', e.target.value)}
          placeholder="用逗号分隔，例如：美食,博物馆"
        />
      </label>

      {apiError && (
        <div className="banner banner-error" role="alert">
          <strong>
            {apiError.status ? `请求失败（${apiError.status}）` : '请求失败'}
          </strong>
          <p>{apiError.message}</p>
        </div>
      )}

      {loading && (
        <div className="banner banner-pending" role="status">
          正在生成行程：查询地点、天气与网页资料后调用模型，通常需要一段时间，请勿重复提交。
        </div>
      )}

      <button type="submit" disabled={loading}>
        {loading ? '生成中…' : '生成行程'}
      </button>
    </form>
  )
}
