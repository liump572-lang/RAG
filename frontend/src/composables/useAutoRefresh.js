import { ref, onMounted, onUnmounted, onActivated, onDeactivated } from 'vue'

export function useAutoRefresh(fetchFn, intervalMs = 30000) {
  const lastRefreshed = ref(null)
  const isRefreshing = ref(false)
  let timer = null
  let stopped = false
  let activatedOnce = false

  async function refresh() {
    if (isRefreshing.value) return
    isRefreshing.value = true
    try {
      await fetchFn()
      lastRefreshed.value = new Date()
    } finally {
      isRefreshing.value = false
    }
  }

  function startPolling() {
    stopPolling()
    stopped = false
    if (intervalMs > 0) {
      timer = setInterval(() => {
        if (!stopped) refresh()
      }, intervalMs)
    }
  }

  function stopPolling() {
    stopped = true
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  }

  // onMounted handles non-keep-alive scenarios
  onMounted(() => {
    refresh()
    startPolling()
  })

  onUnmounted(() => {
    stopPolling()
  })

  // onActivated handles keep-alive scenarios — skips first call to avoid
  // double-fetch with onMounted
  onActivated(() => {
    if (activatedOnce) {
      refresh()
    } else {
      activatedOnce = true
    }
    startPolling()
  })

  onDeactivated(() => {
    stopPolling()
  })

  return { lastRefreshed, isRefreshing, refresh, stopPolling, startPolling }
}
