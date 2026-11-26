import { useEffect, useRef, useState } from 'react'
import './App.css'
import {
  createPlan,
  createEditDraft,
  confirmEditDraft,
  deletePlan,
  getPreferences,
  getPlan,
  listSavedPlans,
  parseRequest,
  PlanApiError,
  savePlan,
  sendChat,
  updatePlanDay,
  type CreatePlanResponse,
  type EditDayRequest,
  type SavedPlanSummary,
} from './api'
import ChatComposer from './ChatComposer'
import HistoryPanel from './HistoryPanel'
import PlanResultView from './PlanResultView'
import PlanDetails from './PlanDetails'
import MapPanel from './MapPanel'
import NewChatView from './NewChatView'
import ResizeHandle from './ResizeHandle'
import FloatingWorkspace from './FloatingWorkspace'
import DraggableDetails from './DraggableDetails'
import { findReplacementTargets, type ActivityTarget } from './editIntent'
import { prepareActivityRemoval } from './removeActivity'
import { replacementCandidates } from './replacementCandidates'
import { formatParseReply, mergeParsedFields, missingTripFields, summarizeTripFields, toRequestBody, validateTripForm, type TripFormValues } from './tripRequest'

type Notice = { kind: 'success' | 'error'; text: string } | null

interface ChatMessage {
  role: 'user' | 'assistant'
  text: string
  planCard?: boolean
  pending?: boolean
  activityChoice?: { target: ActivityTarget; selected?: 'remove' | 'alternatives'; candidateId?: string; busy?: boolean; feedback?: string; replaced?: boolean }
}

interface Chat {
  id: string
  title: string
  titleSource: 'auto' | 'manual'
  plan: CreatePlanResponse | null
  messages: ChatMessage[]
  draft: string
  parsing: boolean
  generation: 'idle' | 'loading' | 'error' | 'ready'
  generationError: string
  formOpen: boolean
  prefill: TripFormValues | null
  formKey: number
}

function createChat(): Chat {
  return{
    id: crypto.randomUUID(),
    title: '新的旅游规划',
    titleSource: 'auto',
    plan: null,
    messages: [],
    draft: '',
    parsing: false,
    generation: 'idle',
    generationError: '',
    formOpen: false,
    prefill: null,
    formKey: 0,
  }
}

type Theme = 'light' | 'dark'

function initialTheme(): Theme {
  try {
    const saved = localStorage.getItem('travel-agent-theme')
    if (saved === 'light' || saved === 'dark') return saved
  } catch {
    // 浏览器禁用本地存储时，仍可在当前页面切换主题。
  }
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

// 三栏宽度限制（像素）。中间栏为自适应剩余空间，并保证不小于 CENTER_MIN。
const LEFT_MIN = 160
const LEFT_MAX = 420
const RIGHT_MIN = 240
const RIGHT_MAX = 800
const CENTER_MIN = 320
const HANDLE_WIDTH = 6

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value))

// 对话先拥有独立 ID，生成行程后再关联后端 plan_id。
// 聊天状态只在当前页面内存中；刷新后只从后端恢复已保存行程。
export default function App() {
  const [theme, setTheme] = useState<Theme>(initialTheme)
  const [chats, setChats] = useState<Chat[]>(() => [createChat()])
  const [savedIds, setSavedIds] = useState<Set<string>>(() => new Set())
  const [savedPlans, setSavedPlans] = useState<SavedPlanSummary[]>([])
  const [pinnedIds, setPinnedIds] = useState<Set<string>>(() => readIdSet('travel-agent-pinned'))
  const [archivedIds, setArchivedIds] = useState<Set<string>>(() => readIdSet('travel-agent-archived'))
  const [defaultPreferences, setDefaultPreferences] = useState<string[]>([])
  const [preferencesLoaded, setPreferencesLoaded] = useState(false)
  const [openingPlanId, setOpeningPlanId] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState(chats[0].id)
  const [saving, setSaving] = useState(false)
  const [savingEdit, setSavingEdit] = useState(false)
  const [notice, setNotice] = useState<Notice>(null)
  const [detailsDetached, setDetailsDetached] = useState(false)
  const [mapDayIndex, setMapDayIndex] = useState(0)
  const [leftWidth, setLeftWidth] = useState(240)
  const [rightWidth, setRightWidth] = useState(420)
  const widthsAtDragStart = useRef({ left: 240, right: 420 })
  const sendingChats = useRef(new Set<string>())
  const removingPlans = useRef(new Set<string>())
  const confirmingPlans = useRef(new Set<string>())

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    try {
      localStorage.setItem('travel-agent-theme', theme)
    } catch {
      // 存储不可用不影响当前页面的主题。
    }
  }, [theme])

  useEffect(() => {
    try {
      localStorage.setItem('travel-agent-pinned', JSON.stringify([...pinnedIds]))
      localStorage.setItem('travel-agent-archived', JSON.stringify([...archivedIds]))
    } catch { /* 存储不可用时仅在当前页面保留。 */ }
  }, [pinnedIds, archivedIds])

  const currentChat = chats.find((chat) => chat.id === selectedId)!
  const selected = currentChat.plan
  const isSaved = selected !== null && savedIds.has(selected.plan_id)
  useEffect(() => {
    let cancelled = false

    listSavedPlans()
      .then((result) => {
        if (!cancelled) setSavedPlans(result.plans)
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setNotice({
            kind: 'error',
            text: `读取已保存行程列表失败：${errorText(error, '请稍后刷新页面。')}`,
          })
        }
      })

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    getPreferences()
      .then((result) => {
        if (!cancelled) {
          setDefaultPreferences(result.preferences)
          setPreferencesLoaded(true)
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setNotice({
            kind: 'error',
            text: `读取默认偏好失败：${errorText(error, '请稍后刷新页面。')}`,
          })
        }
      })
    return () => { cancelled = true }
  }, [])
  function updateChat(id: string, changes: Partial<Chat>) {
    setChats((prev) =>
      prev.map((chat) => {
        if (chat.id !== id) return chat

        const next = { ...chat, ...changes }
        const destination =
          changes.plan?.itinerary.request.destination ??
          changes.prefill?.destination

        if (next.titleSource === 'auto' && destination?.trim()) {
          next.title = `${destination.trim()}旅游攻略`
        }

        return next
      }),
    )
  }

  function handleNewChat() {
    setNotice(null)
    const chat = createChat()
    setChats((prev) => [chat, ...prev])
    setSelectedId(chat.id)
  }

  function handleGenerated(chatId: string, result: CreatePlanResponse) {
    setChats((prev) => prev.map((chat) => chat.id === chatId
      ? { ...chat, plan: result, generation: 'ready', generationError: '', formOpen: false, messages: [...chat.messages, { role: 'assistant', text: '', planCard: true }] }
      : chat))
  }

  function handleSelect(planId: string) {
    setNotice(null)
    setSelectedId(planId)
  }

  async function handleOpenSaved(planId: string) {
    if (openingPlanId !== null) return

    setOpeningPlanId(planId)
    setNotice(null)
    try {
      const result = await getPlan(planId)
      const existing = chats.find((chat) => chat.plan?.plan_id === planId)

      if (existing) {
        updateChat(existing.id, { plan: result })
    setSelectedId(existing.id)
      } else {
        const chat = createChat()
        chat.plan = result
        chat.title = `${result.itinerary.request.destination}旅游攻略`
        setChats((prev) => [chat, ...prev])
    setSelectedId(chat.id)
      }
      setSavedIds((prev) => new Set(prev).add(planId))
    } catch (error) {
      setNotice({
        kind: 'error',
        text: `重新打开行程失败：${errorText(error, '请稍后重试。')}`,
      })
    } finally {
      setOpeningPlanId(null)
    }
  }

  function handleRename(chatId: string, title: string) {
    const trimmedTitle = title.trim()
    if (!trimmedTitle) return

    updateChat(chatId, {
      title: trimmedTitle,
      titleSource: 'manual',
    })
  }

  async function handleDeleteArchived(id: string, title: string, planId: string | null) {
    if (deletingId || !window.confirm(`永久删除“${title}”？已保存的行程记录也会从本地数据库删除，且无法恢复。`)) return
    setDeletingId(id)
    try {
      if (planId) await deletePlan(planId)
      const removedChatIds = chats.filter((chat) => chat.id === id || chat.plan?.plan_id === id).map((chat) => chat.id)
      const remaining = chats.filter((chat) => !removedChatIds.includes(chat.id))
      const nextChats = remaining.length ? remaining : [createChat()]
      setChats(nextChats)
      if (removedChatIds.includes(selectedId)) {
    setSelectedId(nextChats[0].id)
      }
      if (planId) {
        setSavedPlans((prev) => prev.filter((plan) => plan.plan_id !== planId))
        setSavedIds((prev) => { const next = new Set(prev); next.delete(planId); return next })
      }
      setPinnedIds((prev) => { const next = new Set(prev); next.delete(id); return next })
      setArchivedIds((prev) => { const next = new Set(prev); next.delete(id); return next })
      setNotice({ kind: 'success', text: `已永久删除“${title}”。` })
    } catch (error) {
      setNotice({ kind: 'error', text: `删除失败：${errorText(error, '请稍后重试。')}` })
    } finally {
      setDeletingId(null)
    }
  }

  function appendMessages(key: string, added: ChatMessage[]) {
    setChats((prev) => prev.map((chat) => chat.id === key
      ? { ...chat, messages: [...chat.messages, ...added] }
      : chat))
  }

  function removePendingMessage(chatId: string) {
    setChats((prev) => prev.map((chat) => chat.id === chatId
      ? { ...chat, messages: chat.messages.filter((message) => !message.pending) }
      : chat))
  }

  function chooseActivityAction(chatId: string, messageIndex: number, action: 'remove' | 'alternatives') {
    if (action === 'remove') {
      void removeChosenActivity(chatId, messageIndex)
      return
    }
    const chat = chats.find((item) => item.id === chatId)
    const choice = chat?.messages[messageIndex]?.activityChoice
    if (!choice || !chat?.plan || choice.selected) return
    const candidates = replacementCandidates(chat.plan.itinerary, choice.target)
    setChats((prev) => prev.map((chat) => chat.id === chatId
      ? { ...chat, messages: chat.messages.map((message, index) => index === messageIndex && message.activityChoice
        ? { ...message, activityChoice: { ...message.activityChoice, selected: action, feedback: candidates.length
          ? '可在下方或地图上选择一个候选地点；行程尚未修改。'
          : '这份行程没有其他可用地点；后续步骤再补充搜索。' } }
        : message) }
      : chat))
  }

  function patchActivityChoice(chatId: string, messageIndex: number, changes: Partial<NonNullable<ChatMessage['activityChoice']>>) {
    setChats((prev) => prev.map((chat) => chat.id === chatId
      ? { ...chat, messages: chat.messages.map((message, index) => index === messageIndex && message.activityChoice
        ? { ...message, activityChoice: { ...message.activityChoice, ...changes } }
        : message) }
      : chat))
  }

  async function confirmChosenReplacement(chatId: string, messageIndex: number) {
    const chat = chats.find((item) => item.id === chatId)
    const choice = chat?.messages[messageIndex]?.activityChoice
    if (!chat?.plan || !choice?.candidateId || choice.busy || confirmingPlans.current.has(chat.plan.plan_id)) return
    if (!savedIds.has(chat.plan.plan_id)) {
      patchActivityChoice(chatId, messageIndex, { feedback: '请先保存行程，再确认替换。' })
      return
    }
    const day = chat.plan.itinerary.daily_plans.find((item) => item.day_number === choice.target.dayNumber)
    if (day?.activities[choice.target.activityIndex]?.place_id !== choice.target.placeId) {
      patchActivityChoice(chatId, messageIndex, { feedback: '行程已变化，请重新选择要替换的活动。' })
      return
    }
    confirmingPlans.current.add(chat.plan.plan_id)
    patchActivityChoice(chatId, messageIndex, { busy: true, feedback: '' })
    try {
      const result = await createEditDraft(chat.plan.plan_id, choice.target, choice.candidateId)
      if (result.draft.candidate_place_id !== choice.candidateId || result.draft.original_place_id !== choice.target.placeId) {
        throw new Error('替换内容与当前选择不一致，请重试。')
      }
      const updated = await confirmEditDraft(chat.plan.plan_id, result.draft)
      updateChat(chatId, { plan: updated })
      patchActivityChoice(chatId, messageIndex, { busy: false, candidateId: undefined, replaced: true, feedback: '已保存替换，地图已同步。' })
    } catch (error) {
      patchActivityChoice(chatId, messageIndex, { busy: false, feedback: errorText(error, '替换失败，原行程已保留。') })
    } finally {
      confirmingPlans.current.delete(chat.plan.plan_id)
    }
  }

  async function removeChosenActivity(chatId: string, messageIndex: number) {
    const chat = chats.find((item) => item.id === chatId)
    const choice = chat?.messages[messageIndex]?.activityChoice
    const plan = chat?.plan
    if (!choice || !plan || choice.busy || choice.selected || removingPlans.current.has(plan.plan_id)) return
    const target = choice.target
    const day = plan.itinerary.daily_plans.find((item) => item.day_number === target.dayNumber)
    if (!day || day.activities[target.activityIndex]?.place_id !== target.placeId) {
      patchActivityChoice(chatId, messageIndex, { feedback: '行程已变化，请重新说出要去掉的地点。' })
      return
    }
    if (!savedIds.has(plan.plan_id)) {
      patchActivityChoice(chatId, messageIndex, { feedback: '请先保存行程，再去掉这项活动。' })
      return
    }
    if (day.activities.length === 1) {
      patchActivityChoice(chatId, messageIndex, { feedback: '当天至少需要保留一项活动，不能直接去掉。' })
      return
    }
    removingPlans.current.add(plan.plan_id)
    patchActivityChoice(chatId, messageIndex, { busy: true, feedback: '' })
    try {
      const body = prepareActivityRemoval(day, target.activityIndex)
      const updated = await updatePlanDay(plan.plan_id, target.dayNumber, body)
      updateChat(chatId, { plan: updated })
      patchActivityChoice(chatId, messageIndex, { busy: false, selected: 'remove', feedback: '已从行程中去掉，地图已同步。' })
    } catch (error) {
      patchActivityChoice(chatId, messageIndex, { busy: false, feedback: errorText(error, '删除失败，原行程已保留。') })
    } finally {
      removingPlans.current.delete(plan.plan_id)
    }
  }

  async function handleSend(text: string) {
    const chatId = currentChat.id
    if (sendingChats.current.has(chatId)) return
    updateChat(chatId, { draft: '' })

    // 已生成行程：编辑请求走现有定位，其他消息进入自然对话。
    if (selected) {
      const targets = findReplacementTargets(text, selected.itinerary)
      if (targets && targets.length > 0) {
        let reply = ''
        let activityChoice: ChatMessage['activityChoice']
        if (targets.length === 1) {
          const target = targets[0]
          reply = `第 ${target.dayNumber} 天的“${target.placeName}”（第 ${target.activityIndex + 1} 项）不想去了。你想直接去掉，还是看看其他地点？`
          activityChoice = { target }
        } else if (targets.length > 1) {
          reply = `找到多个可能的活动：${targets.map((target) => `第 ${target.dayNumber} 天第 ${target.activityIndex + 1} 项“${target.placeName}”`).join('、')}。请指出要替换哪一项；现在行程尚未修改。`
        }
        appendMessages(chatId, [{ role: 'user', text }, { role: 'assistant', text: reply, activityChoice }])
        return
      }

      const history = currentChat.messages
        .filter((message) => !message.pending && !message.planCard && message.text)
        .slice(-12)
        .map((message) => ({ role: message.role, content: message.text }))
      appendMessages(chatId, [{ role: 'user', text }])
      sendingChats.current.add(chatId)
      updateChat(chatId, { parsing: true })
      try {
        const result = await sendChat(text, selected.plan_id, history)
        if (result.kind === 'edit_target' && result.target) {
          const day = selected.itinerary.daily_plans.find((item) => item.day_number === result.target!.day_number)
          const activity = day?.activities[result.target.activity_index]
          const place = selected.itinerary.places.find((item) => item.place_id === result.target!.place_id)
          if (activity?.place_id === result.target.place_id && place) {
            const target: ActivityTarget = {
              dayNumber: result.target.day_number,
              activityIndex: result.target.activity_index,
              placeId: result.target.place_id,
              placeName: place.name,
            }
            appendMessages(chatId, [{ role: 'assistant', text: `第 ${target.dayNumber} 天的“${target.placeName}”（第 ${target.activityIndex + 1} 项）不想去了。你想直接去掉，还是看看其他地点？`, activityChoice: { target } }])
          } else {
            appendMessages(chatId, [{ role: 'assistant', text: '行程已变化，请重新说明要调整的地点。' }])
          }
        } else {
          appendMessages(chatId, [{ role: 'assistant', text: result.message }])
        }
      } catch (error) {
        appendMessages(chatId, [{ role: 'assistant', text: `处理失败：${errorText(error, '请稍后重试。')}` }])
      } finally {
        sendingChats.current.delete(chatId)
        updateChat(chatId, { parsing: false })
      }
      return
    }

    // 每次只解析本条消息，再与当前聊天已识别的字段合并；缺失项留在对话中追问。
    appendMessages(chatId, [{ role: 'user', text }])
    sendingChats.current.add(chatId)
    updateChat(chatId, { parsing: true })
    try {
      const result = await parseRequest(text)
      const merged = mergeParsedFields(currentChat.prefill, result.fields)
      const missing = missingTripFields(merged)
      const issues = Object.values(validateTripForm(merged))
      updateChat(chatId, { prefill: merged, formKey: currentChat.formKey + 1 })
      if (missing.length || issues.length) {
        appendMessages(chatId, [{
          role: 'assistant',
          text: formatParseReply({ summary: summarizeTripFields(merged), missing, issues: missing.length ? [] : issues }),
        }])
      } else {
        appendMessages(chatId, [{ role: 'assistant', text: '信息已齐全，正在生成行程…', pending: true }])
        updateChat(chatId, { generation: 'loading', generationError: '' })
        const plan = await createPlan(toRequestBody(merged))
        removePendingMessage(chatId)
        handleGenerated(chatId, plan)
      }
    } catch (error) {
      removePendingMessage(chatId)
      setChats((prev) => prev.map((chat) => chat.id === chatId && chat.generation === 'loading'
        ? { ...chat, generation: 'error', generationError: errorText(error, '请稍后重试。') } : chat))
      appendMessages(chatId, [
        {
          role: 'assistant',
          text: `处理失败：${errorText(error, '请稍后重试。')} 已识别的信息保留在表单中。`,
        },
      ])
    } finally {
      sendingChats.current.delete(chatId)
      updateChat(chatId, { parsing: false })
    }
  }

  async function handleSave() {
    if (!selected || saving || isSaved) return
    setSaving(true)
    setNotice(null)
    try {
      await savePlan(selected.plan_id)
      setSavedIds((prev) => new Set(prev).add(selected.plan_id))
      setNotice({ kind: 'success', text: '行程已保存；刷新页面后可在左侧重新打开。' })
      try {
        const result = await listSavedPlans()
        setSavedPlans(result.plans)
      } catch {
        setNotice({ kind: 'success', text: '行程已保存；列表暂未刷新，可刷新页面后重新打开。' })
      }
    } catch (error) {
      setNotice({ kind: 'error', text: errorText(error, '保存失败，请稍后重试。') })
    } finally {
      setSaving(false)
    }
  }

  async function handleEditDay(dayNumber: number, body: EditDayRequest) {
    if (!selected || !isSaved || savingEdit) return

    setSavingEdit(true)
    setNotice(null)
    try {
      const updated = await updatePlanDay(selected.plan_id, dayNumber, body)
      updateChat(currentChat.id, { plan: updated })
      setNotice({ kind: 'success', text: `第 ${dayNumber} 天已更新，地图已同步。` })
    } catch (error) {
      setNotice({ kind: 'error', text: errorText(error, '编辑失败，原行程已保留。') })
      throw error
    } finally {
      setSavingEdit(false)
    }
  }

  function beginDrag() {
    widthsAtDragStart.current = { left: leftWidth, right: rightWidth }
  }

  // 左分隔条：向右拖动增加左栏宽度。
  function dragLeft(dx: number) {
    setLeftWidth(clamp(widthsAtDragStart.current.left + dx, LEFT_MIN, LEFT_MAX))
  }

  // 右分隔条：向左拖动增加行程详情栏宽度。
  function dragRight(dx: number) {
    setRightWidth(clamp(widthsAtDragStart.current.right - dx, RIGHT_MIN, RIGHT_MAX))
  }

  const gridColumns = `${leftWidth}px ${HANDLE_WIDTH}px minmax(${CENTER_MIN}px, 1fr)`
  const latestChoice = [...currentChat.messages].reverse().find((message) => message.activityChoice)?.activityChoice
  const activeChoice = latestChoice?.selected === 'alternatives' ? latestChoice : undefined
  const previewCandidates = selected && activeChoice ? replacementCandidates(selected.itinerary, activeChoice.target) : []
  const previewTarget = selected && activeChoice && selected.itinerary.daily_plans
    .find((day) => day.day_number === activeChoice.target.dayNumber)?.activities[activeChoice.target.activityIndex]?.place_id === activeChoice.target.placeId
    ? activeChoice.target : null

  function selectPreviewCandidate(placeId: string) {
    const messageIndex = currentChat.messages.findLastIndex((message) => message.activityChoice === activeChoice)
    if (messageIndex < 0 || !previewCandidates.some((place) => place.place_id === placeId)) return
    patchActivityChoice(currentChat.id, messageIndex, { candidateId: placeId, feedback: '' })
  }

  return (
    <div className="map-workspace">
      <div className="workspace-map" aria-label="背景地图">
        <MapPanel days={selected?.map_days ?? []} background selectedDayIndex={mapDayIndex}
          preview={previewTarget ? { target: previewTarget, candidates: previewCandidates, selectedId: activeChoice?.candidateId } : undefined}
          onSelectCandidate={selectPreviewCandidate} />
      </div>
      {selected && selected.map_days.length > 0 && (
        <div className="background-day-tabs day-tabs" role="group" aria-label="背景地图日期">
          {selected.map_days.map((day, index) => (
            <button key={day.day_number} type="button" className={index === Math.min(mapDayIndex, selected.map_days.length - 1) ? 'day-tab active' : 'day-tab'}
              aria-pressed={index === Math.min(mapDayIndex, selected.map_days.length - 1)} onClick={() => setMapDayIndex(index)}>第 {day.day_number} 天</button>
          ))}
        </div>
      )}
      <div className={`workspace-panels${detailsDetached ? ' details-detached' : ''}`} style={{ gridTemplateColumns: `minmax(486px, 1fr) ${HANDLE_WIDTH}px ${rightWidth}px` }}>
      <FloatingWorkspace>
      <div className="layout" style={{ gridTemplateColumns: gridColumns }}>
      <aside className="pane pane-history" aria-label="对话列表">
        <HistoryPanel
          chats={chats}
          savedPlans={savedPlans}
          selectedId={selectedId}
          onSelect={handleSelect}
          onOpenSaved={handleOpenSaved}
          onNewChat={handleNewChat}
          onRename={handleRename}
          pinnedIds={pinnedIds}
          archivedIds={archivedIds}
          onTogglePin={(id) => setPinnedIds((current) => toggleId(current, id))}
          onToggleArchive={(id) => setArchivedIds((current) => toggleId(current, id))}
          onDeleteArchived={handleDeleteArchived}
          deletingId={deletingId}
          theme={theme}
          onToggleTheme={() => setTheme((current) => current === 'dark' ? 'light' : 'dark')}
          defaultPreferences={defaultPreferences}
          preferencesLoaded={preferencesLoaded}
          onPreferencesSaved={setDefaultPreferences}
        />
      </aside>

      <ResizeHandle label="调整左栏宽度" onDragStart={beginDrag} onDrag={dragLeft} />

      <main className="pane chat-pane" aria-label="对话">
        <div className="chat-scroll">
          {notice && !selected && (
            <div
              className={notice.kind === 'error' ? 'banner banner-error' : 'banner banner-success'}
              role={notice.kind === 'error' ? 'alert' : 'status'}
            >
              {notice.text}
            </div>
          )}

          {chats.filter((chat) => !chat.plan).map((chat) => (
            <div key={chat.id} hidden={chat.id !== selectedId}>
              <NewChatView
                defaultPreferences={defaultPreferences}
                preferencesLoaded={preferencesLoaded}
                formOpen={chat.formOpen}
                onFormOpenChange={(open) => updateChat(chat.id, { formOpen: open })}
                prefill={chat.prefill}
                formKey={chat.formKey}
                onGenerated={(result) => handleGenerated(chat.id, result)}
                onGenerationChange={(generation, generationError = '') => updateChat(chat.id, { generation, generationError })}
              />
            </div>
          ))}

          {currentChat.messages.map((message, index) => (
            message.planCard && selected ? (
              <PlanResultView
                key={`${selected.plan_id}-${index}`}
                plan={selected}
                onOpen={() => document.getElementById('plan-details')?.scrollIntoView({ block: 'nearest', inline: 'nearest' })}
                active
              />
            ) : (
              <div key={index} className={`chat-bubble ${message.role}`}>
                {message.text}
                {message.activityChoice && (
                  <div className="activity-choice-actions" aria-label="活动处理方式">
                    <button type="button" disabled={Boolean(message.activityChoice.selected) || Boolean(message.activityChoice.busy)}
                      onClick={() => chooseActivityAction(currentChat.id, index, 'remove')}>直接去掉</button>
                    <button type="button" disabled={Boolean(message.activityChoice.selected) || Boolean(message.activityChoice.busy)}
                      onClick={() => chooseActivityAction(currentChat.id, index, 'alternatives')}>看看其他地点</button>
                    {message.activityChoice.selected && (
                      <span role="status">{message.activityChoice.selected === 'remove' ? '已从行程中去掉，地图已同步。' : message.activityChoice.replaced ? '已完成替换。' : '已选择看看其他地点；行程尚未修改。'}</span>
                    )}
                    {selected && message.activityChoice.selected === 'alternatives' && (
                      <div className="activity-candidates">
                        {replacementCandidates(selected.itinerary, message.activityChoice.target).map((place) => (
                          <button key={place.place_id} type="button" disabled={message.activityChoice?.busy}
                            aria-pressed={message.activityChoice?.candidateId === place.place_id}
                            onClick={() => patchActivityChoice(currentChat.id, index, { candidateId: place.place_id, feedback: '' })}>{place.name}</button>
                        ))}
                        {message.activityChoice.candidateId && <button type="button" disabled={message.activityChoice.busy || !isSaved}
                          onClick={() => void confirmChosenReplacement(currentChat.id, index)}>确认替换</button>}
                        {message.activityChoice.candidateId && !isSaved && <span role="status">请先保存行程，再确认替换。</span>}
                        <span role="status">{message.activityChoice.feedback}</span>
                      </div>
                    )}
                    {message.activityChoice.busy && <span role="status">正在处理…</span>}
                    {message.activityChoice.feedback && !message.activityChoice.selected && <span role="status">{message.activityChoice.feedback}</span>}
                  </div>
                )}
              </div>
            )
          ))}
          {selected && !currentChat.messages.some((message) => message.planCard) && (
            <PlanResultView
              key={selected.plan_id}
              plan={selected}
                onOpen={() => document.getElementById('plan-details')?.scrollIntoView({ block: 'nearest', inline: 'nearest' })}
                active
            />
          )}
        </div>

        <div className="chat-dock">
          <ChatComposer
            draft={currentChat.draft}
            onDraftChange={(draft) => updateChat(currentChat.id, { draft })}
            onSend={handleSend}
            disabled={currentChat.parsing}
            placeholder={currentChat.parsing ? '正在解析需求…' : undefined}
          />
        </div>
      </main>

      </div>
      </FloatingWorkspace>

      <ResizeHandle label="调整行程详情栏宽度" onDragStart={beginDrag} onDrag={dragRight} />

      <DraggableDetails onDetach={() => setDetailsDetached(true)} onDock={() => setDetailsDetached(false)}>
      <section id="plan-details" className="pane pane-details" aria-label="行程详情">
        <h2>行程详情</h2>
        {selected ? (
          <PlanDetails key={currentChat.id} plan={selected} notice={notice} isSaved={isSaved}
            saving={saving} savingEdit={savingEdit} onSave={handleSave} onEditDay={handleEditDay} />
        ) : currentChat.generation === 'loading' ? (
          <div className="banner banner-pending" role="status" aria-live="polite">
            旅行计划正在生成中…
            <p>正在整理地点、天气与路线，请稍候。</p>
          </div>
        ) : currentChat.generation === 'error' ? (
          <div className="banner banner-error" role="alert">
            <strong>旅行计划生成失败</strong>
            <p>{currentChat.generationError}</p>
            <button type="button" onClick={() => updateChat(currentChat.id, { formOpen: true })}>检查需求并重试</button>
          </div>
        ) : <p className="muted details-empty">生成旅行计划后，在这里查看行程详情。</p>}
      </section>
      </DraggableDetails>
      </div>
    </div>
  )
}

function errorText(error: unknown, fallback: string): string {
  if (error instanceof PlanApiError) return error.message
  return fallback
}

function readIdSet(key: string): Set<string> {
  try {
    const value: unknown = JSON.parse(localStorage.getItem(key) ?? '[]')
    return new Set(Array.isArray(value) ? value.filter((id): id is string => typeof id === 'string') : [])
  } catch { return new Set() }
}

function toggleId(current: ReadonlySet<string>, id: string): Set<string> {
  const next = new Set(current)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  return next
}
