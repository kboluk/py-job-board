const form = document.querySelector('form#search')
const listEl = document.getElementById('results')
const count = document.getElementById('count')

// A) Intercept search form (submit *and* live input are fine)
form.addEventListener('input', debounce(pushFilter, 100))
form.addEventListener('submit', e => { e.preventDefault(); pushFilter() })

function pushFilter () {
  const formData = new FormData(form)
  const body = {
    q: formData.get('q') || '',
    tag: formData.getAll('tag') || ''
  }
  fetch('/search', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', 'x-csrf-token': formData.get('_csrf') },
    body: JSON.stringify(body)
  })
  // ignore response – SSE will deliver results
}

function debounce (callback, wait) {
  let timeoutId = null
  return function (...args) {
    window.clearTimeout(timeoutId)
    timeoutId = window.setTimeout(() => {
      callback.apply(null, args)
    }, wait)
  }
}

// B) Open SSE stream
const stream = new EventSource('/events')
stream.addEventListener('results', e => {
  const { html, count: n } = JSON.parse(e.data)
  listEl.innerHTML = html
  count.textContent = n
})
