import { useState, useRef, useEffect, useMemo } from 'react'
import { toast } from 'sonner'
import {
  addCreator,
  fetchMetadata,
  scanDirectory,
  selectFolder,
  triggerBatchPipeline,
  triggerDownloadBatch,
  triggerLocalTranscribe,
  type DouyinMetadataResponse,
  type ScannedFile,
  type Task,
  type Creator,
} from '@/lib/api'
import { getTaskDisplayState, getTaskError, getTaskMessage } from '@/lib/task-utils'

interface UseDiscoveryActionsParams {
  url: string
  tasks: Task[]
  activeTaskId: string | null
  setActiveTaskId: (id: string | null) => void
  storeFetchCreators: () => Promise<Creator[]>
}

export function useDiscoveryActions({
  url,
  tasks,
  activeTaskId,
  setActiveTaskId,
  storeFetchCreators,
}: UseDiscoveryActionsParams) {
  const [isFetching, setIsFetching] = useState(false)
  const [metadata, setMetadata] = useState<DouyinMetadataResponse | null>(null)
  const [selectedUrls, setSelectedUrls] = useState<Set<string>>(new Set())
  const [followedCreatorUids, setFollowedCreatorUids] = useState<Set<string>>(new Set())
  const [isFollowingCreator, setIsFollowingCreator] = useState(false)
  const [resultMsg, setResultMsg] = useState<{ type: 'success' | 'warning' | 'error'; text: string; error?: string } | null>(null)
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false)
  const [pendingFetchUrl, setPendingFetchUrl] = useState<string | null>(null)

  const [localDir, setLocalDir] = useState('')
  const [isScanning, setIsScanning] = useState(false)
  const [scannedFiles, setScannedFiles] = useState<ScannedFile[]>([])
  const [selectedLocalFiles, setSelectedLocalFiles] = useState<Set<string>>(new Set())
  const [deleteAfterTranscribe, setDeleteAfterTranscribe] = useState(false)

  const abortControllerRef = useRef<AbortController | null>(null)

  const activeTask = useMemo(
    () => (activeTaskId ? tasks.find((t) => t.task_id === activeTaskId) || null : null),
    [activeTaskId, tasks]
  )

  const taskState = activeTask ? getTaskDisplayState(activeTask) : null
  const taskMessage = activeTask ? getTaskMessage(activeTask) : ''
  const taskError = activeTask ? getTaskError(activeTask) : ''
  const isFollowed = metadata ? followedCreatorUids.has(metadata.creator.uid) : false

  useEffect(() => {
    storeFetchCreators()
      .then((creators) => setFollowedCreatorUids(new Set(creators.map((c) => c.uid))))
      .catch((err) => console.error('获取创作者列表失败:', err))
  }, [storeFetchCreators])

  useEffect(() => {
    return () => { abortControllerRef.current?.abort() }
  }, [])

  useEffect(() => {
    if (!activeTask) return
    if (taskState === 'success' || taskState === 'failed' || taskState === 'stale') {
      setActiveTaskId(null)
      queueMicrotask(() => {
        if (taskState === 'success') {
          setResultMsg({ type: 'success', text: taskMessage || '任务已完成' })
          toast.success(taskMessage || '任务已完成')
        } else {
          setResultMsg({
            type: 'error',
            text: taskMessage || '任务执行失败',
            error: taskError || '请到任务中心查看详情。',
          })
          toast.error(taskMessage || '任务执行失败')
        }
      })
    }
  }, [activeTask, setActiveTaskId, taskError, taskMessage, taskState])

  const _doFetch = async (fetchUrl: string) => {
    abortControllerRef.current?.abort()
    abortControllerRef.current = new AbortController()

    setIsFetching(true)
    setMetadata(null)
    setSelectedUrls(new Set())
    setResultMsg(null)

    try {
      const data = await fetchMetadata(fetchUrl, 12, abortControllerRef.current.signal)
      setMetadata(data)
    } catch (error) {
      if (error instanceof Error && (error.name === 'AbortError' || error.message === 'canceled')) return
      const errMsg = error instanceof Error ? error.message : '未知错误'
      toast.error(`获取创作者预览失败: ${errMsg}`)
    } finally {
      setIsFetching(false)
    }
  }

  const handleFetch = async (e: React.FormEvent) => {
    e.preventDefault()
    let processedUrl = url.trim()
    if (!processedUrl) return
    if (!processedUrl.startsWith('http://') && !processedUrl.startsWith('https://')) {
      processedUrl = `https://${processedUrl}`
    }

    if (selectedUrls.size > 0) {
      setPendingFetchUrl(processedUrl)
      setConfirmDialogOpen(true)
      return
    }

    await _doFetch(processedUrl)
  }

  const handleConfirmFetch = () => {
    setConfirmDialogOpen(false)
    if (pendingFetchUrl) {
      _doFetch(pendingFetchUrl)
      setPendingFetchUrl(null)
    }
  }

  const handleToggleSelect = (videoUrl: string) => {
    const next = new Set(selectedUrls)
    if (next.has(videoUrl)) next.delete(videoUrl)
    else next.add(videoUrl)
    setSelectedUrls(next)
  }

  const handleToggleAll = () => {
    if (!metadata) return
    const allUrls = metadata.videos.map((v) => v.video_url)
    const allSelected = allUrls.length > 0 && allUrls.every((u) => selectedUrls.has(u))
    setSelectedUrls(allSelected ? new Set() : new Set(allUrls))
  }

  const handleProcessBatch = async () => {
    if (selectedUrls.size === 0) return
    setResultMsg(null)
    try {
      const result = await triggerBatchPipeline(Array.from(selectedUrls))
      setActiveTaskId(result.task_id)
      toast.success('已提交下载并转写任务')
    } catch {
      // interceptor already toasts
    }
  }

  const handleDownloadBatch = async () => {
    if (selectedUrls.size === 0) return
    setResultMsg(null)
    try {
      const result = await triggerDownloadBatch(Array.from(selectedUrls))
      setActiveTaskId(result.task_id)
      toast.success('已提交仅下载任务')
    } catch {
      // interceptor already toasts
    }
  }

  const handleFollowCreator = async () => {
    if (!metadata) return
    let processedUrl = url.trim()
    if (!processedUrl.startsWith('http://') && !processedUrl.startsWith('https://')) {
      processedUrl = `https://${processedUrl}`
    }

    setIsFollowingCreator(true)
    try {
      const result = await addCreator(processedUrl)
      setFollowedCreatorUids((prev) => new Set(prev).add(result.creator.uid))
      toast.success(result.status === 'created' ? '已加入创作者列表' : '该创作者已在列表中')
    } catch {
      // interceptor already toasts
    } finally {
      setIsFollowingCreator(false)
    }
  }

  const handleScanDir = async (dir?: string) => {
    const directory = dir ?? localDir.trim()
    if (!directory) return
    setIsScanning(true)
    setScannedFiles([])
    setSelectedLocalFiles(new Set())
    try {
      const data = await scanDirectory(directory)
      setLocalDir(data.directory)
      setScannedFiles(data.files)
      if (data.files.length === 0) {
        toast('该目录下没有找到音视频文件')
      } else {
        setSelectedLocalFiles(new Set(data.files.map((f) => f.path)))
      }
    } catch {
      toast.error('扫描目录失败，请检查路径是否正确')
    } finally {
      setIsScanning(false)
    }
  }

  const handleSelectFolder = async () => {
    setIsScanning(true)
    try {
      const result = await selectFolder()
      if (result.directory) {
        await handleScanDir(result.directory)
      }
    } catch (error) {
      const err = error as { response?: { data?: { detail?: string } } } | null
      const msg = err?.response?.data?.detail || '选择文件夹失败'
      if (msg !== '未选择文件夹或选择器不可用') {
        toast.error(msg)
      }
    } finally {
      setIsScanning(false)
    }
  }

  const handleToggleLocalFile = (path: string) => {
    setSelectedLocalFiles((prev) => {
      const next = new Set(prev)
      if (next.has(path)) next.delete(path)
      else next.add(path)
      return next
    })
  }

  const handleLocalTranscribe = async () => {
    if (selectedLocalFiles.size === 0) return
    setResultMsg(null)
    try {
      const result = await triggerLocalTranscribe(Array.from(selectedLocalFiles), deleteAfterTranscribe, localDir.trim())
      setActiveTaskId(result.task_id)
      toast.success(`已提交 ${selectedLocalFiles.size} 个文件的转写任务`)
      setScannedFiles([])
      setSelectedLocalFiles(new Set())
    } catch {
      // interceptor already toasts
    }
  }

  return {
    isFetching,
    metadata,
    selectedUrls,
    isFollowingCreator,
    isFollowed,
    resultMsg,
    confirmDialogOpen,
    localDir,
    isScanning,
    scannedFiles,
    selectedLocalFiles,
    deleteAfterTranscribe,
    activeTask,
    taskState,
    taskMessage,
    taskError,
    abortControllerRef,
    handleFetch,
    handleConfirmFetch,
    handleToggleSelect,
    handleToggleAll,
    handleProcessBatch,
    handleDownloadBatch,
    handleFollowCreator,
    handleScanDir,
    handleSelectFolder,
    handleToggleLocalFile,
    handleLocalTranscribe,
    setConfirmDialogOpen,
    setLocalDir,
    setDeleteAfterTranscribe,
  }
}
