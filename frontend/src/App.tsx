import { useState, useEffect, useCallback } from 'react'
import { listExpenses, getVersion } from './api'
import type { Expense } from './api'
import { ExpenseForm } from './components/ExpenseForm'
import { ExpenseList } from './components/ExpenseList'

function App() {
  const [expenses, setExpenses] = useState<Expense[]>([])
  const [fetchError, setFetchError] = useState<string | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [version, setVersion] = useState<string | null>(null)

  const fetchExpenses = useCallback(async () => {
    setDeleteError(null)
    try {
      const data = await listExpenses()
      setExpenses(data)
      setFetchError(null)
    } catch (err) {
      setFetchError(err instanceof Error ? err.message : 'Failed to load expenses')
    }
  }, [])

  useEffect(() => {
    fetchExpenses()
    getVersion().then(setVersion)
  }, [fetchExpenses])

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: '2rem' }}>
      <h1>Finance Tracker</h1>
      <h2>Add Expense</h2>
      <ExpenseForm onExpenseAdded={fetchExpenses} />
      <h2>Expenses</h2>
      {fetchError && <p style={{ color: 'red' }}>{fetchError}</p>}
      {deleteError && <p style={{ color: 'red' }}>{deleteError}</p>}
      <ExpenseList
        expenses={expenses}
        onDeleted={fetchExpenses}
        onDeleteError={setDeleteError}
      />
      {version !== null && (
        <footer style={{ marginTop: '2rem', color: '#888', fontSize: '0.8rem', textAlign: 'center' }}>
          version: {version}
        </footer>
      )}
    </div>
  )
}

export default App
